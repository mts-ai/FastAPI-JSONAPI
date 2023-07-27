"""This module is a CRUD interface between resource managers and the sqlalchemy ORM"""
import logging
from typing import TYPE_CHECKING, Any, Iterable, List, Optional, Tuple, Type

from sqlalchemy import func, select
from sqlalchemy.exc import DatabaseError, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.orm.collections import InstrumentedList
from sqlalchemy.sql import Delete, Select

from fastapi_jsonapi.data_layers.base import BaseDataLayer
from fastapi_jsonapi.data_layers.data_typing import TypeModel, TypeSchema
from fastapi_jsonapi.data_layers.filtering.sqlalchemy import create_filters
from fastapi_jsonapi.data_layers.sorting.sqlalchemy import create_sorts
from fastapi_jsonapi.exceptions import (
    HTTPException,
    InternalServerError,
    InvalidInclude,
    ObjectNotFound,
    RelatedObjectNotFound,
    RelationNotFound,
)
from fastapi_jsonapi.querystring import PaginationQueryStringManager, QueryStringManager
from fastapi_jsonapi.schema import (
    BaseJSONAPIItemInSchema,
    BaseJSONAPIRelationshipDataToManySchema,
    BaseJSONAPIRelationshipDataToOneSchema,
    get_model_field,
    get_related_schema,
)
from fastapi_jsonapi.schema_base import RelationshipInfo
from fastapi_jsonapi.splitter import SPLIT_REL

if TYPE_CHECKING:
    pass


log = logging.getLogger(__name__)


class SqlalchemyDataLayer(BaseDataLayer):
    """Sqlalchemy data layer"""

    def __init__(
        self,
        schema: Type[TypeSchema],
        model: Type[TypeModel],
        session: AsyncSession,
        disable_collection_count: bool = False,
        default_collection_count: int = -1,
        id_name_field: Optional[str] = None,
        url_id_field: str = "id",
        eagerload_includes: bool = True,
        query: Optional[Select] = None,
        **kwargs: Any,
    ):
        """
        Initialize an instance of SqlalchemyDataLayer.

        :params schema:
        :params model:
        :params disable_collection_count: Resource's attribute `disable_collection_count`
                                          has to be bool or list/tuple with exactly 2 values!
        :params default_collection_count: For example `disable_collection_count = (True, 999)`
        :params id_name_field: Первичный ключ модели
        :params url_field: название переменной из FastAPI, в которой придёт значение первичного ключа.
        :params eagerload_includes: Use eagerload feature of sqlalchemy to optimize data retrieval
                                    for include querystring parameter.
        :params query: подготовленный заранее запрос.
        :params kwargs: initialization parameters of an SqlalchemyDataLayer instance
        """
        super().__init__(
            model=model,
            url_id_field=url_id_field,
            id_name_field=id_name_field,
            **kwargs,
        )

        self.disable_collection_count: bool = disable_collection_count
        self.default_collection_count: int = default_collection_count
        self.schema = schema
        self.session = session
        self.eagerload_includes_ = eagerload_includes
        self._query = query

    async def apply_relationships(self, obj: TypeModel, data_create: BaseJSONAPIItemInSchema) -> None:
        """
        TODO: move generic code to another method

        :param obj:
        :param data_create:
        :return:
        """
        relationships = data_create.relationships  # type: PydanticBaseModel
        if relationships is None:
            return

        schema_fields = self.schema.__fields__ or {}
        for relation_name, relationship_in in relationships:  # type: str, RelationshipInfoSchema
            if relationship_in is None:
                continue

            field = schema_fields.get(relation_name)
            if field is None:
                # should not happen if schema is built properly
                # there may be an error if schema and schema_in are different
                log.warning("field for %s in schema %s not found", relation_name, self.schema.__name__)
                continue

            if "relationship" not in field.field_info.extra:
                log.warning(
                    "relationship info for %s in schema %s extra not found",
                    relation_name,
                    self.schema.__name__,
                )
                continue

            relationship_info: RelationshipInfo = field.field_info.extra["relationship"]
            # todo: use alias (custom names)!!
            # field.field_info.alias
            # field.field_info.title

            # ...
            related_model = getattr(obj.__class__, relation_name).property.mapper.class_

            if relationship_info.many:
                assert isinstance(relationship_in, BaseJSONAPIRelationshipDataToManySchema)
                related_data = await self.get_related_objects_list(
                    related_model=related_model,
                    related_id_field=relationship_info.id_field_name,
                    ids=[r.id for r in relationship_in.data],
                )
            else:
                assert isinstance(relationship_in, BaseJSONAPIRelationshipDataToOneSchema)
                related_data = await self.get_related_object(
                    related_model=related_model,
                    related_id_field=relationship_info.id_field_name,
                    id_value=relationship_in.data.id,
                )
            # todo: relation name may be different?
            setattr(obj, relation_name, related_data)

    async def create_object(self, data_create: BaseJSONAPIItemInSchema, view_kwargs: dict) -> TypeModel:
        """
        Create an object through sqlalchemy.

        :params model_kwargs: the data validated by pydantic.
        :params view_kwargs: kwargs from the resource view.
        :return:
        """
        # todo: pydantic v2 model_dump()
        model_kwargs = data_create.attributes.dict()
        await self.before_create_object(model_kwargs=model_kwargs, view_kwargs=view_kwargs)

        # TODO: accept custom `id` ( Client-Generated IDs )
        #  https://jsonapi.org/format/#crud-creating-client-ids
        obj = self.model(**model_kwargs)
        await self.apply_relationships(obj, data_create)

        self.session.add(obj)
        try:
            await self.session.commit()
        except DatabaseError:
            log.exception("Could not create object with data create %s", data_create)
            msg = "Object creation error"
            raise HTTPException(msg, pointer="/data")
        except Exception as e:
            await self.session.rollback()
            msg = f"Object creation error: {e}"
            raise HTTPException(msg, pointer="/data")

        await self.after_create_object(obj=obj, model_kwargs=model_kwargs, view_kwargs=view_kwargs)

        return obj

    def get_object_id_field_name(self):
        """
        compound key may cause errors
        :return:
        """
        return self.id_name_field or inspect(self.model).primary_key[0].key

    async def get_object(self, view_kwargs: dict, qs: Optional[QueryStringManager] = None) -> TypeModel:
        """
        Retrieve an object through sqlalchemy.

        :params view_kwargs: kwargs from the resource view
        :params qs:
        :return DeclarativeMeta: an object from sqlalchemy
        """
        await self.before_get_object(view_kwargs)

        filter_field = self.get_object_id_field()
        filter_value = view_kwargs[self.url_id_field]

        query = self.retrieve_object_query(view_kwargs, filter_field, filter_value)

        if qs is not None:
            query = self.eagerload_includes(query, qs)

        try:
            obj = (await self.session.execute(query)).scalar_one()
        except NoResultFound:
            msg = f"Resource {self.model.__name__} `{filter_value}` not found"
            raise ObjectNotFound(
                msg,
                parameter=self.url_id_field,
            )

        await self.after_get_object(obj, view_kwargs)

        return obj

    async def get_collection_count(self, query: Select, qs: QueryStringManager, view_kwargs: dict) -> int:
        """
        :params query: SQLAlchemy query
        :params qs: QueryString
        :params view_kwargs: view kwargs
        :return:
        """
        if self.disable_collection_count is True:
            return self.default_collection_count

        return (await self.session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()

    async def get_collection(self, qs: QueryStringManager, view_kwargs: Optional[dict] = None) -> Tuple[int, list]:
        """
        Retrieve a collection of objects through sqlalchemy.

        :params qs: a querystring manager to retrieve information from url.
        :params view_kwargs: kwargs from the resource view.
        :return: the number of object and the list of objects.
        """
        view_kwargs = view_kwargs or {}

        await self.before_get_collection(qs, view_kwargs)

        query = self.query(view_kwargs)

        if filters_qs := qs.filters:
            query = self.filter_query(query, filters_qs)

        if sorts := qs.get_sorts(schema=self.schema):
            query = self.sort_query(query, sorts)

        objects_count = await self.get_collection_count(query, qs, view_kwargs)

        if self.eagerload_includes_:
            query = self.eagerload_includes(query, qs)

        query = self.paginate_query(query, qs.pagination)

        collection = (await self.session.execute(query)).scalars().all()

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

        :params obj: an object from sqlalchemy.
        :params data: the data validated by pydantic.
        :params view_kwargs: kwargs from the resource view.
        :return: True if object have changed else False.
        """
        new_data = data_update.attributes.dict()
        has_updated = False

        for field_name, new_value in new_data.items():
            # TODO: handle attr not found
            old_value = getattr(obj, field_name)

            if old_value != new_value:
                setattr(obj, field_name, new_value)
                has_updated = True

        try:
            await self.session.commit()
            await self.session.refresh(obj)
        except Exception:  # TODO: handle and specify exc
            await self.session.rollback()
            raise InternalServerError(
                detail="Failed attempt to update data in DB",
            )

        return has_updated

    async def delete_object(self, obj: TypeModel, view_kwargs: dict):
        """
        Delete an object through sqlalchemy.

        :params obj: an item from sqlalchemy.
        :params view_kwargs: kwargs from the resource view.
        """
        try:
            await self.session.delete(obj)
            await self.session.commit()
        except Exception:  # TODO: handle and specify exc
            await self.session.rollback()
            raise InternalServerError(
                detail="Failed attempt to delete data in DB",
            )

    async def delete_objects(self, objects: List[TypeModel], view_kwargs: dict):
        query = Delete(self.model).filter(self.model.id.in_((obj.id for obj in objects)))

        try:
            await self.session.execute(query)
            await self.session.commit()
        except Exception:  # TODO: handle and specify exc
            await self.session.rollback()
            raise InternalServerError(
                detail="Failed attempt to delete data in DB",
            )

    async def create_relationship(
        self,
        json_data: dict,
        relationship_field: str,
        related_id_field: str,
        view_kwargs: dict,
    ) -> bool:
        """
        Create a relationship.

        :params json_data: the request params.
        :params relationship_field: the model attribute used for relationship.
        :params related_id_field: the identifier field of the related model.
        :params view_kwargs: kwargs from the resource view.
        :return: True if relationship have changed else False.
        """
        pass

    async def get_relationship(
        self,
        relationship_field: str,
        related_type_: str,
        related_id_field: str,
        view_kwargs: dict,
    ) -> Tuple[Any, Any]:
        """
        Get a relationship.

        :params relationship_field: the model attribute used for relationship.
        :params related_type_: the related resource type.
        :params related_id_field: the identifier field of the related model.
        :params view_kwargs: kwargs from the resource view.
        :return: the object and related object(s).
        """
        await self.before_get_relationship(relationship_field, related_type_, related_id_field, view_kwargs)

        obj = await self.get_object(view_kwargs)

        if obj is None:
            filter_value = view_kwargs[self.url_id_field]
            msg = f"{self.model.__name__}: {filter_value} not found"
            raise ObjectNotFound(
                msg,
                parameter=self.url_id_field,
            )

        if not hasattr(obj, relationship_field):
            msg = f"{obj.__class__.__name__} has no attribute {relationship_field}"
            raise RelationNotFound(msg)

        related_objects = getattr(obj, relationship_field)

        if related_objects is None:
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
        else:
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

        :params json_data: the request params.
        :params relationship_field: the model attribute used for relationship.
        :params related_id_field: the identifier field of the related model.
        :param view_kwargs: kwargs from the resource view.
        :return: True if relationship have changed else False.
        """
        pass

    async def delete_relationship(
        self,
        json_data: dict,
        relationship_field: str,
        related_id_field: str,
        view_kwargs: dict,
    ):
        """
        Delete a relationship.

        :params json_data: the request params.
        :params relationship_field: the model attribute used for relationship.
        :params related_id_field: the identifier field of the related model.
        :params view_kwargs: kwargs from the resource view.
        """
        pass

    async def get_related_object(
        self,
        related_model: Type[TypeModel],
        related_id_field: str,
        id_value: str,
    ) -> TypeModel:
        """
        Get related object.

        :params related_model: SQLA ORM model class
        :params related_id_field: id field of the related model (usually it's `id`)
        :params id_value: related object id value
        :return: a related SQLA ORM object
        """
        stmt = select(related_model).where(getattr(related_model, related_id_field) == id_value)
        try:
            related_object = (await self.session.execute(stmt)).scalar_one()
        except NoResultFound:
            msg = f"{related_model.__name__}.{related_id_field}: {id_value} not found"
            raise RelatedObjectNotFound(msg)

        return related_object

    async def get_related_objects_list(
        self,
        related_model: Type[TypeModel],
        related_id_field: str,
        ids: list[str],
    ) -> list[TypeModel]:
        """

        :param related_model:
        :param related_id_field:
        :param ids:
        :return:
        """
        # TODO: check ids / count and raise if some objects not found
        stmt = select(related_model).where(getattr(related_model, related_id_field).in_(ids))

        related_objects = (await self.session.execute(stmt)).scalars().all()

        return list(related_objects)

    def filter_query(self, query: Select, filter_info: Optional[list]) -> Select:
        """
        Filter query according to jsonapi 1.0.

        :params query: sqlalchemy query to sort.
        :params filter_info: filter information.
        :params model: an sqlalchemy model.
        :return: the sorted query.
        """
        if filter_info:
            filters, joins = create_filters(model=self.model, filter_info=filter_info, schema=self.schema)
            for i_join in joins:
                query = query.join(*i_join)
            query = query.where(*filters)

        return query

    def sort_query(self, query: Select, sort_info: list) -> Select:
        """
        Sort query according to jsonapi 1.0.

        :params query: sqlalchemy query to sort.
        :params sort_info: sort information.
        :return: the sorted query.
        """
        if sort_info:
            sorts, joins = create_sorts(self.model, sort_info, self.schema)
            for i_join in joins:
                query = query.join(*i_join)
            for i_sort in sorts:
                query = query.order_by(i_sort)
        return query

    def paginate_query(self, query: Select, paginate_info: PaginationQueryStringManager) -> Select:
        """
        Paginate query according to jsonapi 1.0.

        :params query: sqlalchemy queryset.
        :params paginate_info: pagination information.
        :return: the paginated query
        """
        if paginate_info.size == 0 or paginate_info.size is None:
            return query

        query = query.limit(paginate_info.size)
        if paginate_info.number:
            query = query.offset((paginate_info.number - 1) * paginate_info.size)

        return query

    def eagerload_includes(self, query: Select, qs: QueryStringManager) -> Select:
        """
        Use eagerload feature of sqlalchemy to optimize data retrieval for include querystring parameter.

        :params query: sqlalchemy queryset.
        :params qs: a querystring manager to retrieve information from url.
        :return: the query with includes eagerloaded.
        """
        for include in qs.include:
            relation_join_object = None

            current_schema = self.schema
            current_model = self.model
            for related_field_name in include.split(SPLIT_REL):
                try:
                    field_name_to_load = get_model_field(current_schema, related_field_name)
                except Exception as e:
                    raise InvalidInclude(str(e))

                field_to_load: InstrumentedAttribute = getattr(current_model, field_name_to_load)
                is_many = field_to_load.property.uselist
                if relation_join_object is None:
                    relation_join_object = selectinload(field_to_load) if is_many else joinedload(field_to_load)
                elif is_many:
                    relation_join_object = relation_join_object.selectinload(field_to_load)
                else:
                    relation_join_object = relation_join_object.joinedload(field_to_load)

                current_schema = get_related_schema(current_schema, related_field_name)

                # the first entity is Mapper,
                # the second entity is DeclarativeMeta
                current_model = field_to_load.property.entity.entity

            query = query.options(relation_join_object)

        return query

    def retrieve_object_query(
        self,
        view_kwargs: dict,
        filter_field: InstrumentedAttribute,
        filter_value: Any,
    ) -> Select:
        """
        Build query to retrieve object.

        :params view_kwargs: kwargs from the resource view
        :params filter_field: the field to filter on
        :params filter_value: the value to filter with
        :return sqlalchemy query: a query from sqlalchemy
        """
        query: Select = self.query(view_kwargs)
        # noinspection PyNoneFunctionAssignment,PyTypeChecker
        query: Select = query.where(filter_field == filter_value)
        return query

    def query(self, view_kwargs: dict) -> Select:
        """
        Construct the base query to retrieve wanted data.

        :params view_kwargs: kwargs from the resource view
        """
        if self._query is not None:
            return self._query
        return select(self.model)

    async def before_create_object(self, model_kwargs: dict, view_kwargs: dict):
        """
        Provide additional data before object creation.

        :params model_kwargs: the data validated by pydantic.
        :params view_kwargs: kwargs from the resource view.
        """
        pass

    async def after_create_object(self, obj: TypeModel, model_kwargs: dict, view_kwargs: dict):
        """
        Provide additional data after object creation.

        :params obj: an object from data layer.
        :params model_kwargs: the data validated by pydantic.
        :params view_kwargs: kwargs from the resource view.
        """
        pass

    async def before_get_object(self, view_kwargs: dict):
        """
        Make work before to retrieve an object.

        :params view_kwargs: kwargs from the resource view.
        """
        pass

    async def after_get_object(self, obj: Any, view_kwargs: dict):
        """
        Make work after to retrieve an object.

        :params obj: an object from data layer.
        :params view_kwargs: kwargs from the resource view.
        """
        pass

    async def before_get_collection(self, qs: QueryStringManager, view_kwargs: dict):
        """
        Make work before to retrieve a collection of objects.

        :params qs: a querystring manager to retrieve information from url.
        :params view_kwargs: kwargs from the resource view.
        """
        pass

    async def after_get_collection(self, collection: Iterable, qs: QueryStringManager, view_kwargs: dict):
        """
        Make work after to retrieve a collection of objects.

        :params collection: the collection of objects.
        :params qs: a querystring manager to retrieve information from url.
        :params view_kwargs: kwargs from the resource view.
        """
        return collection

    async def before_update_object(self, obj: Any, data: dict, view_kwargs: dict):
        """
        Make checks or provide additional data before update object.

        :params obj: an object from data layer.
        :params data: the data validated by schemas.
        :params view_kwargs: kwargs from the resource view.
        """
        pass

    def after_update_object(self, obj: Any, data: dict, view_kwargs: dict):
        """
        Make work after update object.

        :params obj: an object from data layer.
        :params data: the data validated by schemas.
        :params view_kwargs: kwargs from the resource view.
        """
        pass

    def before_delete_object(self, obj: Any, view_kwargs: dict):
        """
        Make checks before delete object.

        :params obj: an object from data layer.
        :params view_kwargs: kwargs from the resource view.
        """
        pass

    def after_delete_object(self, obj: Any, view_kwargs: dict):
        """
        Make work after delete object.

        :params obj: an object from data layer.
        :params view_kwargs: kwargs from the resource view.
        """
        pass

    def before_create_relationship(
        self,
        json_data: dict,
        relationship_field: str,
        related_id_field: str,
        view_kwargs: dict,
    ):
        """
        Make work before to create a relationship.

        :params json_data: the request params.
        :params relationship_field: the model attribute used for relationship.
        :params related_id_field: the identifier field of the related model.
        :params view_kwargs: kwargs from the resource view.
        :return boolean: True if relationship have changed else False.
        """
        pass

    def after_create_relationship(
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

        :params obj: an object from data layer.
        :params updated: True if object was updated else False.
        :params json_data: the request params.
        :params relationship_field: the model attribute used for relationship.
        :params related_id_field: the identifier field of the related model.
        :params view_kwargs: kwargs from the resource view.
        :return boolean: True if relationship have changed else False.
        """
        pass

    async def before_get_relationship(
        self,
        relationship_field: str,
        related_type_: str,
        related_id_field: str,
        view_kwargs: dict,
    ):
        """
        Make work before to get information about a relationship.

        :params str relationship_field: the model attribute used for relationship.
        :params str related_type_: the related resource type.
        :params str related_id_field: the identifier field of the related model.
        :params dict view_kwargs: kwargs from the resource view.
        :return tuple: the object and related object(s).
        """
        pass

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

        :params obj: an object from data layer.
        :params related_objects: related objects of the object.
        :params relationship_field: the model attribute used for relationship.
        :params related_type_: the related resource type.
        :params related_id_field: the identifier field of the related model.
        :params view_kwargs: kwargs from the resource view.
        :return tuple: the object and related object(s).
        """
        pass

    def before_update_relationship(
        self,
        json_data: dict,
        relationship_field: str,
        related_id_field: str,
        view_kwargs: dict,
    ):
        """
        Make work before to update a relationship.

        :params json_data: the request params.
        :params relationship_field: the model attribute used for relationship.
        :params related_id_field: the identifier field of the related model.
        :params view_kwargs: kwargs from the resource view.
        :return boolean: True if relationship have changed else False.
        """
        pass

    def after_update_relationship(
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

        :params obj: an object from data layer.
        :params updated: True if object was updated else False.
        :params json_data: the request params.
        :params relationship_field: the model attribute used for relationship.
        :params related_id_field: the identifier field of the related model.
        :params view_kwargs: kwargs from the resource view.
        :return boolean: True if relationship have changed else False.
        """
        pass

    def before_delete_relationship(
        self,
        json_data: dict,
        relationship_field: str,
        related_id_field: str,
        view_kwargs: dict,
    ):
        """
        Make work before to delete a relationship.

        :params json_data: the request params.
        :params relationship_field: the model attribute used for relationship.
        :params related_id_field: the identifier field of the related model.
        :params view_kwargs: kwargs from the resource view.
        """
        pass

    def after_delete_relationship(
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

        :params obj: an object from data layer.
        :params updated: True if object was updated else False.
        :params json_data: the request params.
        :params relationship_field: the model attribute used for relationship.
        :params related_id_field: the identifier field of the related model.
        :params view_kwargs: kwargs from the resource view.
        """
        pass
