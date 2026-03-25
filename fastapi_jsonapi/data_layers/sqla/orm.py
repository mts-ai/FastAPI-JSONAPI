"""This module is a CRUD interface between resource managers and the sqlalchemy ORM"""

from __future__ import annotations

import logging
from typing import Any, Iterable, Literal, Optional, Type

from pydantic import BaseModel
from sqlalchemy.exc import MissingGreenlet
from sqlalchemy.ext.asyncio import AsyncSession, AsyncSessionTransaction
from sqlalchemy.orm import joinedload, load_only, selectinload
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.orm.collections import InstrumentedList
from sqlalchemy.sql import Select
from sqlalchemy.sql.expression import BinaryExpression

from fastapi_jsonapi.data_layers.base import BaseDataLayer
from fastapi_jsonapi.data_layers.sqla.base_model import BaseSQLA
from fastapi_jsonapi.data_layers.sqla.query_building import (
    build_filter_expressions,
    build_sort_expressions,
    prepare_relationships_info,
    relationships_info_storage,
)
from fastapi_jsonapi.data_typing import TypeModel
from fastapi_jsonapi.exceptions import (
    InternalServerError,
    InvalidInclude,
    ObjectNotFound,
    RelatedObjectNotFound,
    RelationNotFound,
)
from fastapi_jsonapi.querystring import QueryStringManager
from fastapi_jsonapi.schema import (
    BaseJSONAPIItemInSchema,
)
from fastapi_jsonapi.storages.models_storage import models_storage
from fastapi_jsonapi.storages.schemas_storage import schemas_storage
from fastapi_jsonapi.views import RelationshipRequestInfo

log = logging.getLogger(__name__)


class SqlalchemyDataLayer(BaseDataLayer):
    """Sqlalchemy data layer"""

    def __init__(
        self,
        model: Type[TypeModel],
        session: AsyncSession,
        resource_type: str,
        disable_collection_count: bool = False,
        default_collection_count: int = -1,
        id_name_field: Optional[str] = None,
        url_id_field: str = "id",
        eagerload_includes: bool = True,
        query: Optional[Select] = None,
        auto_convert_id_to_column_type: bool = True,
        **kwargs: Any,
    ):
        """
        Initialize an instance of SqlalchemyDataLayer.

        :param model:
        :param disable_collection_count:
        :param default_collection_count:
        :param id_name_field: Первичный ключ модели
        :param url_field: название переменной из FastAPI, в которой придёт значение первичного ключа.
        :param eagerload_includes: Use eagerload feature of sqlalchemy to optimize data retrieval
                                    for include querystring parameter.
        :param query: подготовленный заранее запрос.
        :param kwargs: initialization parameters of an SqlalchemyDataLayer instance
        """
        super().__init__(
            model=model,
            resource_type=resource_type,
            url_id_field=url_id_field,
            id_name_field=id_name_field,
            disable_collection_count=disable_collection_count,
            default_collection_count=default_collection_count,
            **kwargs,
        )

        self._base_sql = BaseSQLA()
        self._query = query

        self.session = session
        self.eagerload_includes_ = eagerload_includes
        self.auto_convert_id_to_column_type = auto_convert_id_to_column_type
        self.transaction: Optional[AsyncSessionTransaction] = None

    async def atomic_start(
        self,
        previous_dl: Optional[SqlalchemyDataLayer] = None,
    ):
        self.is_atomic = True
        if previous_dl:
            self.session = previous_dl.session
            if previous_dl.transaction:
                self.transaction = previous_dl.transaction
                return None

        self.transaction = self.session.begin()
        await self.transaction.start()

    async def atomic_end(
        self,
        success: bool = True,
        exception: Optional[Exception] = None,
    ):
        if success:
            await self.transaction.commit()
        else:
            await self.transaction.rollback()

    def prepare_id_value(
        self,
        col: InstrumentedAttribute,
        value: Any,
    ) -> Any:
        """
        Convert value to the required python type.

        Type is declared on the SQLA column.

        :param col:
        :param value:
        :return:
        """
        if not self.auto_convert_id_to_column_type:
            return value

        py_type = col.type.python_type
        if not isinstance(value, py_type):
            value = py_type(value)

        return value

    @classmethod
    async def check_object_has_relationship_or_raise(
        cls,
        obj: TypeModel,
        relation_name: str,
    ):
        """
        Checks that there is relationship with relation_name in obj

        :param obj:
        :param relation_name:
        """
        try:
            hasattr(obj, relation_name)
        except MissingGreenlet:
            raise InternalServerError(
                detail=(
                    f"Error of loading the {relation_name!r} relationship. "
                    f"Please add this relationship to include query parameter explicitly."
                ),
                parameter="include",
            )

    async def apply_relationships(
        self,
        obj: TypeModel,
        data_create: BaseJSONAPIItemInSchema,
        action_trigger: Literal["create", "update"],
    ) -> tuple[dict[str, Optional[TypeModel]], dict[str, list[TypeModel]]]:
        """
        Handles relationships passed in request

        :param obj:
        :param data_create:
        :param action_trigger: indicates which one operation triggered relationships applying
        :return:
        """
        to_one, to_many = {}, {}
        relationships: BaseModel = data_create.relationships
        if relationships is None:
            return to_one, to_many

        for relation_name, relationship_in in relationships:
            if relationship_in is None:
                continue

            relationship_info = schemas_storage.get_relationship_info(
                resource_type=self.resource_type,
                operation_type=action_trigger,
                field_name=relation_name,
            )
            if relationship_info is None:
                log.warning("Not found relationship %s for resource_type %s", relation_name, self.resource_type)
                continue

            related_model = models_storage.get_model(relationship_info.resource_type)
            related_data = []
            if relationship_in.data:
                related_data = await self.get_related_objects(
                    related_model=related_model,
                    related_id_field=relationship_info.id_field_name,
                    ids=[r.id for r in relationship_in.data] if relationship_info.many else [relationship_in.data.id],
                )

            await self.check_object_has_relationship_or_raise(obj, relation_name)

            if relationship_info.many:
                to_many[relation_name] = related_data
            elif related_data:
                related_data, *_ = related_data
                to_one[relation_name] = related_data
            else:
                to_one[relation_name] = None
        return to_one, to_many

    async def create_object(
        self,
        data_create: BaseJSONAPIItemInSchema,
        view_kwargs: dict,
    ) -> TypeModel:
        """
        Create an object through sqlalchemy.

        :param data_create: the data validated by pydantic.
        :param view_kwargs: kwargs from the resource view.
        :return:
        """
        log.debug("Create object with data %s", data_create)
        model_kwargs = self._apply_client_generated_id(data_create, data_create.attributes.model_dump())
        await self.before_create_object(model_kwargs, view_kwargs)

        obj = self.model(**model_kwargs)
        to_one, to_many = await self.apply_relationships(obj, data_create, "create")
        model_kwargs.update({**to_one, **to_many})
        obj = await self._base_sql.create(
            session=self.session,
            model=obj,
            resource_type=self.resource_type,
            commit=not self.is_atomic,
            id_=view_kwargs.get(self.url_id_field),
            **model_kwargs,
        )

        await self.after_create_object(obj, model_kwargs, view_kwargs)
        return obj

    def get_fields_options(
        self,
        resource_type: str,
        qs: QueryStringManager,
        required_to_load: Optional[set] = None,
    ) -> set:
        required_to_load = required_to_load or set()

        if resource_type not in qs.fields:
            return set()

        # empty str means skip all attributes
        if "" not in qs.fields[resource_type]:
            required_to_load.update(field_name for field_name in qs.fields[resource_type])

        return self.get_load_only_options(
            resource_type=resource_type,
            field_names=required_to_load,
        )

    @staticmethod
    def get_load_only_options(
        resource_type: str,
        field_names: Iterable[str],
    ) -> set:
        model = models_storage.get_model(resource_type)
        options = {
            load_only(
                getattr(
                    model,
                    models_storage.get_model_id_field_name(resource_type),
                ),
            ),
        }

        for field_name in field_names:
            options.add(load_only(getattr(model, field_name)))

        return options

    def get_relationship_request_filters(
        self,
        model_id_field: InstrumentedAttribute,
        parent_obj_id: Any,
        parent_resource_type: str,
        relationship_name: str,
    ) -> list[BinaryExpression]:
        parent_model = models_storage.get_model(parent_resource_type)
        parent_id_field = models_storage.get_object_id_field(parent_resource_type)
        parent_relationship_field = getattr(parent_model, relationship_name)
        info = schemas_storage.get_relationship_info(
            resource_type=parent_resource_type,
            operation_type="get",
            field_name=relationship_name,
        )
        stmt = self._base_sql.query(
            model=self.model,
            fields=[model_id_field],
            select_from=parent_model,
            filters=[parent_id_field == parent_obj_id],
            size=None if info.many else 1,
            join=[(self.model, parent_relationship_field)],
        )
        return [model_id_field.in_(stmt)]

    async def get_object(
        self,
        view_kwargs: dict,
        qs: Optional[QueryStringManager] = None,
        relationship_request_info: Optional[RelationshipRequestInfo] = None,
    ) -> TypeModel:
        """
        Retrieve an object through sqlalchemy.

        :param view_kwargs: kwargs from the resource view
        :param qs:
        :param relationship_request_info:
        :return DeclarativeMeta: an object from sqlalchemy
        """
        await self.before_get_object(view_kwargs)

        model_id_field = models_storage.get_object_id_field(self.resource_type)
        filter_value = self.prepare_id_value(model_id_field, view_kwargs[self.url_id_field])

        options = set()
        if qs is not None:
            options.update(self.eagerload_includes(qs))
            options.update(
                self.get_fields_options(
                    resource_type=self.resource_type,
                    qs=qs,
                    required_to_load=set(view_kwargs.get("required_to_load", set())),
                ),
            )

        if relationship_request_info is None:
            filters = [model_id_field == filter_value]
        else:
            filters = self.get_relationship_request_filters(
                model_id_field=model_id_field,
                parent_obj_id=filter_value,
                parent_resource_type=relationship_request_info.parent_resource_type,
                relationship_name=relationship_request_info.relationship_name,
            )

        query = self._base_sql.query(
            model=self.model,
            filters=filters,
            options=options,
            stmt=self._query,
        )
        obj = await self._base_sql.one_or_raise(
            session=self.session,
            model=self.model,
            filters=[model_id_field == filter_value],
            stmt=query,
        )

        await self.after_get_object(obj, view_kwargs)
        return obj

    async def get_collection(
        self,
        qs: QueryStringManager,
        view_kwargs: Optional[dict] = None,
        relationship_request_info: Optional[RelationshipRequestInfo] = None,
    ) -> tuple[int, list]:
        """
        Retrieve a collection of objects through sqlalchemy.

        :param qs: a querystring manager to retrieve information from url.
        :param view_kwargs: kwargs from the resource view.
        :param relationship_request_info: indicates that method was called in fetch relationship request and
                                          contains some related data
        :return: the number of object and the list of objects.
        """
        view_kwargs = view_kwargs or {}
        await self.before_get_collection(qs, view_kwargs)
        relationship_paths = prepare_relationships_info(
            model=self.model,
            schema=self.schema,
            resource_type=self.resource_type,
            filter_info=qs.filters,
            sorting_info=qs.sorts,
        )
        relationships_info = [
            relationships_info_storage.get_info(self.resource_type, relationship_path)
            for relationship_path in relationship_paths
        ]

        options = self.get_fields_options(self.resource_type, qs)
        if self.eagerload_includes_:
            options.update(self.eagerload_includes(qs))

        filters = self.get_filter_expressions(qs) or []
        if relationship_request_info is not None:
            model_id_field = models_storage.get_object_id_field(self.resource_type)
            filters.extend(
                self.get_relationship_request_filters(
                    model_id_field=model_id_field,
                    parent_obj_id=self.prepare_id_value(model_id_field, relationship_request_info.parent_obj_id),
                    parent_resource_type=relationship_request_info.parent_resource_type,
                    relationship_name=relationship_request_info.relationship_name,
                ),
            )

        query = self._base_sql.query(
            model=self.model,
            filters=filters,
            jsonapi_join=relationships_info,
            number=qs.pagination.number,
            options=options,
            order=self.get_sort_expressions(qs),
            size=qs.pagination.size,
            stmt=self._query,
        )
        collection = await self._base_sql.all(
            session=self.session,
            stmt=query,
        )

        objects_count = self.default_collection_count
        if not self.disable_collection_count:
            count_query = self._base_sql.query(
                model=self.model,
                filters=filters,
                jsonapi_join=relationships_info,
                stmt=self._query,
            )
            objects_count = await self._base_sql.count(
                session=self.session,
                stmt=count_query,
            )

        collection = await self.after_get_collection(collection, qs, view_kwargs)
        return objects_count, list(collection)

    async def update_object(
        self,
        obj: TypeModel,
        data_update: BaseJSONAPIItemInSchema,
        view_kwargs: dict,
    ) -> bool:
        """
        Update an object through sqlalchemy.

        :param obj: an object from sqlalchemy.
        :param data_update: the data validated by pydantic.
        :param view_kwargs: kwargs from the resource view.
        :return: True if object have changed else False.
        """
        new_data = data_update.attributes.model_dump(exclude_unset=True)
        to_one, to_many = await self.apply_relationships(obj, data_update, "update")
        await self.before_update_object(obj, new_data, view_kwargs)

        new_data.update({**to_one, **to_many})
        obj = await self._base_sql.update(
            session=self.session,
            model=obj,
            resource_type=self.resource_type,
            commit=not self.is_atomic,
            id_=view_kwargs.get(self.url_id_field),
            **new_data,
        )

        await self.after_update_object(obj, new_data, view_kwargs)
        return obj

    async def delete_object(
        self,
        obj: TypeModel,
        view_kwargs: dict,
    ):
        """
        Delete an object through sqlalchemy.

        :param obj: an item from sqlalchemy.
        :param view_kwargs: kwargs from the resource view.
        """
        await self.before_delete_object(obj, view_kwargs)

        await self._base_sql.delete(
            session=self.session,
            model=self.model,
            filters=[self.model.id == obj.id],
            resource_type=self.resource_type,
            commit=not self.is_atomic,
            id_=view_kwargs.get(self.url_id_field),
            **view_kwargs,
        )

        await self.after_delete_object(obj, view_kwargs)

    async def delete_objects(
        self,
        objects: list[TypeModel],
        view_kwargs: dict,
    ):
        await self.before_delete_objects(objects, view_kwargs)

        await self._base_sql.delete(
            session=self.session,
            model=self.model,
            filters=[self.model.id.in_((obj.id for obj in objects))],
            resource_type=self.resource_type,
            commit=not self.is_atomic,
            id_=view_kwargs.get(self.url_id_field),
            **view_kwargs,
        )

        await self.after_delete_objects(objects, view_kwargs)

    async def create_relationship(
        self,
        json_data: dict,
        relationship_field: str,
        related_id_field: str,
        view_kwargs: dict,
    ) -> bool:
        """
        Create a relationship.

        :param json_data: the request params.
        :param relationship_field: the model attribute used for relationship.
        :param related_id_field: the identifier field of the related model.
        :param view_kwargs: kwargs from the resource view.
        :return: True if relationship have changed else False.
        """

    async def get_relationship(
        self,
        relationship_field: str,
        related_type_: str,
        related_id_field: str,
        view_kwargs: dict,
    ) -> tuple[Any, Any]:
        """
        Get a relationship.

        :param relationship_field: the model attribute used for relationship.
        :param related_type_: the related resource type.
        :param related_id_field: the identifier field of the related model.
        :param view_kwargs: kwargs from the resource view.
        :return: the object and related object(s).
        """
        await self.before_get_relationship(relationship_field, related_type_, related_id_field, view_kwargs)

        obj = await self.get_object(view_kwargs)

        if obj is None:
            msg = f"{self.model.__name__}: {view_kwargs[self.url_id_field]} not found"
            raise ObjectNotFound(
                msg,
                parameter=self.url_id_field,
            )

        if not hasattr(obj, relationship_field):
            msg = f"{obj.__class__.__name__} has no attribute {relationship_field}"
            raise RelationNotFound(msg)

        if (related_objects := getattr(obj, relationship_field)) is None:
            return obj, related_objects

        await self.after_get_relationship(
            obj,
            related_objects,
            relationship_field,
            related_type_,
            related_id_field,
            view_kwargs,
        )

        if isinstance(related_objects, InstrumentedList):
            return obj, [{"type": related_type_, "id": getattr(obj_, related_id_field)} for obj_ in related_objects]
        return obj, {"type": related_type_, "id": getattr(related_objects, related_id_field)}

    async def update_relationship(
        self,
        json_data: dict,
        relationship_field: str,
        related_id_field: str,
        view_kwargs: dict,
    ) -> bool:
        """
        Update a relationship

        :param json_data: the request params.
        :param relationship_field: the model attribute used for relationship.
        :param related_id_field: the identifier field of the related model.
        :param view_kwargs: kwargs from the resource view.
        :return: True if relationship have changed else False.
        """

    async def delete_relationship(
        self,
        json_data: dict,
        relationship_field: str,
        related_id_field: str,
        view_kwargs: dict,
    ):
        """
        Delete a relationship.

        :param json_data: the request params.
        :param relationship_field: the model attribute used for relationship.
        :param related_id_field: the identifier field of the related model.
        :param view_kwargs: kwargs from the resource view.
        """

    async def get_related_objects(
        self,
        related_model: TypeModel,
        related_id_field: str,
        ids: list[str],
    ) -> list[TypeModel]:
        """
        Fetch related objects (many)

        :param related_model:
        :param related_id_field:
        :param ids:
        :return:
        """
        id_field = getattr(related_model, related_id_field)
        id_values = [self.prepare_id_value(id_field, id_) for id_ in ids]

        query = self._base_sql.query(
            model=related_model,
            filters=[id_field.in_(id_values)],
        )
        related_objects = await self._base_sql.all(
            session=self.session,
            stmt=query,
        )

        objects = {f"{getattr(obj, related_id_field)}" for obj in related_objects}
        if not_found_ids := set(ids).difference(objects):
            msg = f"Objects for {related_model.__name__} with ids: {list(not_found_ids)} not found"
            raise RelatedObjectNotFound(
                detail=msg,
                pointer="/data",
            )

        return list(related_objects)

    def get_filter_expressions(
        self,
        qs: QueryStringManager,
    ) -> Optional[list[BinaryExpression]]:
        if qs.filters:
            return [
                build_filter_expressions(
                    filter_item={"and": qs.filters},
                    target_model=self.model,
                    target_schema=self.schema,
                    entrypoint_resource_type=self.resource_type,
                ),
            ]

    def get_sort_expressions(
        self,
        qs: QueryStringManager,
    ) -> Optional[list]:
        if qs.sorts:
            return build_sort_expressions(
                sort_items=qs.sorts,
                target_model=self.model,
                target_schema=self.schema,
                entrypoint_resource_type=self.resource_type,
            )

    def eagerload_includes(
        self,
        qs: QueryStringManager,
    ):
        """
        Use eagerload feature of sqlalchemy to optimize data retrieval for include querystring parameter.

        :param qs: a querystring manager to retrieve information from url.
        :return: the query with includes eagerloaded.
        """
        relation_join_objects = []
        for include in qs.include:
            relation_join_object = None

            current_model = self.model
            current_resource_type = self.resource_type

            for related_field_name in include.split("."):
                relationship_info = schemas_storage.get_relationship_info(
                    resource_type=current_resource_type,
                    operation_type="get",
                    field_name=related_field_name,
                )
                if relationship_info is None:
                    msg = (
                        f"Not found relationship {related_field_name!r} from include {include!r} "
                        f"for resource_type {current_resource_type!r}."
                    )
                    raise InvalidInclude(msg)

                field_to_load: InstrumentedAttribute = getattr(current_model, related_field_name)
                is_many = field_to_load.property.uselist
                if relation_join_object is None:
                    relation_join_object = selectinload(field_to_load) if is_many else joinedload(field_to_load)
                elif is_many:
                    relation_join_object = relation_join_object.selectinload(field_to_load)
                else:
                    relation_join_object = relation_join_object.joinedload(field_to_load)

                current_resource_type = relationship_info.resource_type
                current_model = models_storage.get_model(current_resource_type)

                relation_join_object = relation_join_object.options(
                    *self.get_fields_options(
                        resource_type=current_resource_type,
                        qs=qs,
                    ),
                )

            relation_join_objects.append(relation_join_object)

        return relation_join_objects

    async def before_create_object(
        self,
        model_kwargs: dict,
        view_kwargs: dict,
    ):
        """
        Provide additional data before object creation.

        :param model_kwargs: the data validated by pydantic.
        :param view_kwargs: kwargs from the resource view.
        """
        if (id_value := model_kwargs.get("id")) and self.auto_convert_id_to_column_type:
            model_field = models_storage.get_object_id_field(resource_type=self.resource_type)
            model_kwargs.update(id=self.prepare_id_value(model_field, id_value))

    async def after_create_object(
        self,
        obj: TypeModel,
        model_kwargs: dict,
        view_kwargs: dict,
    ):
        """
        Provide additional data after object creation.

        :param obj: an object from data layer.
        :param model_kwargs: the data validated by pydantic.
        :param view_kwargs: kwargs from the resource view.
        """

    async def before_get_object(
        self,
        view_kwargs: dict,
    ):
        """
        Make work before to retrieve an object.

        :param view_kwargs: kwargs from the resource view.
        """

    async def after_get_object(
        self,
        obj: Any,
        view_kwargs: dict,
    ):
        """
        Make work after to retrieve an object.

        :param obj: an object from data layer.
        :param view_kwargs: kwargs from the resource view.
        """

    async def before_get_collection(
        self,
        qs: QueryStringManager,
        view_kwargs: dict,
    ):
        """
        Make work before to retrieve a collection of objects.

        :param qs: a querystring manager to retrieve information from url.
        :param view_kwargs: kwargs from the resource view.
        """

    async def after_get_collection(
        self,
        collection: Iterable,
        qs: QueryStringManager,
        view_kwargs: dict,
    ):
        """
        Make work after to retrieve a collection of objects.

        :param collection: the collection of objects.
        :param qs: a querystring manager to retrieve information from url.
        :param view_kwargs: kwargs from the resource view.
        """
        return collection

    async def before_update_object(
        self,
        obj: Any,
        model_kwargs: dict,
        view_kwargs: dict,
    ):
        """
        Make checks or provide additional data before update object.

        :param obj: an object from data layer.
        :param model_kwargs: the data validated by schemas.
        :param view_kwargs: kwargs from the resource view.
        """

    async def after_update_object(
        self,
        obj: Any,
        model_kwargs: dict,
        view_kwargs: dict,
    ):
        """
        Make work after update object.

        :param obj: an object from data layer.
        :param model_kwargs: the data validated by schemas.
        :param view_kwargs: kwargs from the resource view.
        """

    async def before_delete_object(
        self,
        obj: TypeModel,
        view_kwargs: dict,
    ):
        """
        Make checks before delete object.

        :param obj: an object from data layer.
        :param view_kwargs: kwargs from the resource view.
        """

    async def after_delete_object(
        self,
        obj: TypeModel,
        view_kwargs: dict,
    ):
        """
        Make work after delete object.

        :param obj: an object from data layer.
        :param view_kwargs: kwargs from the resource view.
        """

    async def before_delete_objects(
        self,
        objects: list[TypeModel],
        view_kwargs: dict,
    ):
        """
        Make checks before deleting objects.

        :param objects: an object from data layer.
        :param view_kwargs: kwargs from the resource view.
        """

    async def after_delete_objects(
        self,
        objects: list[TypeModel],
        view_kwargs: dict,
    ):
        """
        Any actions after deleting objects.

        :param objects: an object from data layer.
        :param view_kwargs: kwargs from the resource view.
        """

    async def before_create_relationship(
        self,
        json_data: dict,
        relationship_field: str,
        related_id_field: str,
        view_kwargs: dict,
    ):
        """
        Make work before to create a relationship.

        :param json_data: the request params.
        :param relationship_field: the model attribute used for relationship.
        :param related_id_field: the identifier field of the related model.
        :param view_kwargs: kwargs from the resource view.
        :return boolean: True if relationship have changed else False.
        """

    async def after_create_relationship(
        self,
        obj: Any,
        updated: bool,
        json_data: dict,
        relationship_field: str,
        related_id_field: str,
        view_kwargs: dict,
    ):
        """
        Make work after to create a relationship.

        :param obj: an object from data layer.
        :param updated: True if object was updated else False.
        :param json_data: the request params.
        :param relationship_field: the model attribute used for relationship.
        :param related_id_field: the identifier field of the related model.
        :param view_kwargs: kwargs from the resource view.
        :return boolean: True if relationship have changed else False.
        """

    async def before_get_relationship(
        self,
        relationship_field: str,
        related_type_: str,
        related_id_field: str,
        view_kwargs: dict,
    ):
        """
        Make work before to get information about a relationship.

        :param str relationship_field: the model attribute used for relationship.
        :param str related_type_: the related resource type.
        :param str related_id_field: the identifier field of the related model.
        :param dict view_kwargs: kwargs from the resource view.
        :return tuple: the object and related object(s).
        """

    async def after_get_relationship(
        self,
        obj: Any,
        related_objects: Iterable,
        relationship_field: str,
        related_type_: str,
        related_id_field: str,
        view_kwargs: dict,
    ):
        """
        Make work after to get information about a relationship.

        :param obj: an object from data layer.
        :param related_objects: related objects of the object.
        :param relationship_field: the model attribute used for relationship.
        :param related_type_: the related resource type.
        :param related_id_field: the identifier field of the related model.
        :param view_kwargs: kwargs from the resource view.
        :return tuple: the object and related object(s).
        """

    async def before_update_relationship(
        self,
        json_data: dict,
        relationship_field: str,
        related_id_field: str,
        view_kwargs: dict,
    ):
        """
        Make work before to update a relationship.

        :param json_data: the request params.
        :param relationship_field: the model attribute used for relationship.
        :param related_id_field: the identifier field of the related model.
        :param view_kwargs: kwargs from the resource view.
        :return boolean: True if relationship have changed else False.
        """

    async def after_update_relationship(
        self,
        obj: Any,
        updated: bool,
        json_data: dict,
        relationship_field: str,
        related_id_field: str,
        view_kwargs: dict,
    ):
        """
        Make work after to update a relationship.

        :param obj: an object from data layer.
        :param updated: True if object was updated else False.
        :param json_data: the request params.
        :param relationship_field: the model attribute used for relationship.
        :param related_id_field: the identifier field of the related model.
        :param view_kwargs: kwargs from the resource view.
        :return boolean: True if relationship have changed else False.
        """

    async def before_delete_relationship(
        self,
        json_data: dict,
        relationship_field: str,
        related_id_field: str,
        view_kwargs: dict,
    ):
        """
        Make work before to delete a relationship.

        :param json_data: the request params.
        :param relationship_field: the model attribute used for relationship.
        :param related_id_field: the identifier field of the related model.
        :param view_kwargs: kwargs from the resource view.
        """

    async def after_delete_relationship(
        self,
        obj: Any,
        updated: bool,
        json_data: dict,
        relationship_field: str,
        related_id_field: str,
        view_kwargs: dict,
    ):
        """
        Make work after to delete a relationship.

        :param obj: an object from data layer.
        :param updated: True if object was updated else False.
        :param json_data: the request params.
        :param relationship_field: the model attribute used for relationship.
        :param related_id_field: the identifier field of the related model.
        :param view_kwargs: kwargs from the resource view.
        """
