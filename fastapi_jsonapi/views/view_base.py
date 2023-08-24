import logging
from contextvars import ContextVar
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
    Type,
    Union,
)

from fastapi import Request
from pydantic.fields import ModelField

from fastapi_jsonapi import QueryStringManager, RoutersJSONAPI
from fastapi_jsonapi.data_layers.base import BaseDataLayer
from fastapi_jsonapi.data_typing import (
    TypeModel,
    TypeSchema,
)
from fastapi_jsonapi.schema import (
    JSONAPIObjectSchema,
    JSONAPIResultListMetaSchema,
    get_related_schema,
)
from fastapi_jsonapi.schema_base import BaseModel, RelationshipInfo
from fastapi_jsonapi.schema_builder import JSONAPIObjectSchemas
from fastapi_jsonapi.splitter import SPLIT_REL
from fastapi_jsonapi.views.utils import (
    HTTPMethod,
    HTTPMethodConfig,
)

logger = logging.getLogger(__name__)

previous_resource_type_ctx_var: ContextVar[str] = ContextVar("previous_resource_type_ctx_var")
related_field_name_ctx_var: ContextVar[str] = ContextVar("related_field_name_ctx_var")
relationships_schema_ctx_var: ContextVar[Type[BaseModel]] = ContextVar("relationships_schema_ctx_var")
object_schema_ctx_var: ContextVar[Type[JSONAPIObjectSchema]] = ContextVar("object_schema_ctx_var")
included_object_schema_ctx_var: ContextVar[Type[TypeSchema]] = ContextVar("included_object_schema_ctx_var")
relationship_info_ctx_var: ContextVar[RelationshipInfo] = ContextVar("relationship_info_ctx_var")


class ViewBase:
    """
    Views are inited for each request
    """

    data_layer_cls = BaseDataLayer
    method_dependencies: Dict[HTTPMethod, HTTPMethodConfig] = {}

    def __init__(self, *, request: Request, jsonapi: RoutersJSONAPI, **options):
        self.request: Request = request
        self.jsonapi: RoutersJSONAPI = jsonapi
        self.options: dict = options
        self.query_params: QueryStringManager = QueryStringManager(request=request)

    def _get_data_layer(self, schema: Type[BaseModel], **dl_kwargs):
        return self.data_layer_cls(
            schema=schema,
            model=self.jsonapi.model,
            **dl_kwargs,
        )

    def _get_data_layer_for_detail(self, **kwargs: Any) -> BaseDataLayer:
        """
        :param kwargs: Any extra kwargs for the data layer
        :return:
        """
        return self._get_data_layer(
            schema=self.jsonapi.schema_detail,
            **kwargs,
        )

    def _get_data_layer_for_list(self, **kwargs: Any) -> BaseDataLayer:
        """
        :param kwargs: Any extra kwargs for the data layer
        :return:
        """
        return self._get_data_layer(
            schema=self.jsonapi.schema_list,
            **kwargs,
        )

    def _build_response(self, items_from_db: List[TypeModel], item_schema: Type[BaseModel]):
        return self.process_includes_for_db_items(
            includes=self.query_params.include,
            # as list to reuse helper
            items_from_db=items_from_db,
            item_schema=item_schema,
        )

    def _build_detail_response(self, db_item: TypeModel):
        result_objects, object_schemas, extras = self._build_response([db_item], self.jsonapi.schema_detail)
        # is it ok to do through list?
        result_object = result_objects[0]

        detail_jsonapi_schema = self.jsonapi.schema_builder.build_schema_for_detail_result(
            name=f"Result{self.__class__.__name__}",
            object_jsonapi_schema=object_schemas.object_jsonapi_schema,
            includes_schemas=object_schemas.included_schemas_list,
        )

        return detail_jsonapi_schema(data=result_object, **extras)

    def _build_list_response(self, items_from_db: List[TypeModel], count: int, total_pages: int):
        result_objects, object_schemas, extras = self._build_response(items_from_db, self.jsonapi.schema_list)

        # we need to build a new schema here
        # because we'd like to exclude some fields (relationships, includes, etc)
        list_jsonapi_schema = self.jsonapi.schema_builder.build_schema_for_list_result(
            name=f"Result{self.__class__.__name__}",
            object_jsonapi_schema=object_schemas.object_jsonapi_schema,
            includes_schemas=object_schemas.included_schemas_list,
        )
        return list_jsonapi_schema(
            meta=JSONAPIResultListMetaSchema(count=count, total_pages=total_pages),
            data=result_objects,
            **extras,
        )

    # data preparing below:

    @classmethod
    def get_db_item_id(cls, item_from_db: TypeModel):
        """
        TODO: check if id is None? raise?
        TODO: any another conversion for id to string?
        :param item_from_db:
        :return:
        """
        return str(item_from_db.id)

    @classmethod
    def prepare_related_object_data(
        cls,
        item_from_db: TypeModel,
    ) -> Tuple[Dict[str, Union[str, int]], Optional[TypeSchema]]:
        included_object_schema: Type[TypeSchema] = included_object_schema_ctx_var.get()
        relationship_info: RelationshipInfo = relationship_info_ctx_var.get()
        item_id = cls.get_db_item_id(item_from_db)
        data_for_relationship = {"id": item_id}
        processed_object = included_object_schema(
            id=item_id,
            attributes=item_from_db,
            type=relationship_info.resource_type,
        )

        return data_for_relationship, processed_object

    @classmethod
    def prepare_data_for_relationship(
        cls,
        related_db_item: Union[List[TypeModel], TypeModel],
    ) -> Tuple[Optional[Dict[str, Union[str, int]]], List[TypeSchema]]:
        included_objects = []
        if related_db_item is None:
            return None, included_objects

        data_for_relationship, processed_object = cls.prepare_related_object_data(
            item_from_db=related_db_item,
        )
        if processed_object:
            included_objects.append(processed_object)
        return data_for_relationship, included_objects

    @classmethod
    def update_related_object(
        cls,
        relationship_data: Union[Dict[str, str], List[Dict[str, str]]],
        included_objects: Dict[Tuple[str, str], TypeSchema],
        cache_key: Tuple[str, str],
        related_field_name: str,
    ):
        relationships_schema: Type[BaseModel] = relationships_schema_ctx_var.get()
        object_schema: Type[JSONAPIObjectSchema] = object_schema_ctx_var.get()

        relationship_data_schema = get_related_schema(relationships_schema, related_field_name)
        parent_included_object = included_objects.get(cache_key)
        new_relationships = {}
        if hasattr(parent_included_object, "relationships") and parent_included_object.relationships:
            existing = parent_included_object.relationships or {}
            if isinstance(existing, BaseModel):
                existing = existing.dict()
            new_relationships.update(existing)
        new_relationships.update(
            {
                **{
                    related_field_name: relationship_data_schema(
                        data=relationship_data,
                    ),
                },
            },
        )
        included_objects[cache_key] = object_schema.parse_obj(
            parent_included_object,
        ).copy(
            update={"relationships": new_relationships},
        )

    @classmethod
    def update_known_included(
        cls,
        included_objects: Dict[Tuple[str, str], TypeSchema],
        new_included: List[TypeSchema],
    ):
        for included in new_included:
            included_objects[(included.id, included.type)] = included

    @classmethod
    def process_single_db_item_and_prepare_includes(
        cls,
        parent_db_item: TypeModel,
        included_objects: Dict[Tuple[str, str], TypeSchema],
    ):
        previous_resource_type: str = previous_resource_type_ctx_var.get()
        related_field_name: str = related_field_name_ctx_var.get()

        next_current_db_item = []
        cache_key = (cls.get_db_item_id(parent_db_item), previous_resource_type)
        current_db_item = getattr(parent_db_item, related_field_name)
        current_is_single = False
        if not isinstance(current_db_item, Iterable):
            # hack to do less if/else
            current_db_item = [current_db_item]
            current_is_single = True
        relationship_data_items = []

        for db_item in current_db_item:
            next_current_db_item.append(db_item)
            data_for_relationship, new_included = cls.prepare_data_for_relationship(
                related_db_item=db_item,
            )

            cls.update_known_included(
                included_objects=included_objects,
                new_included=new_included,
            )
            relationship_data_items.append(data_for_relationship)

        if current_is_single:
            # if initially was single, get back one dict
            # hack to do less if/else
            relationship_data_items = relationship_data_items[0]

        cls.update_related_object(
            relationship_data=relationship_data_items,
            included_objects=included_objects,
            cache_key=cache_key,
            related_field_name=related_field_name,
        )

        return next_current_db_item

    @classmethod
    def process_db_items_and_prepare_includes(
        cls,
        parent_db_items: List[TypeModel],
        included_objects: Dict[Tuple[str, str], TypeSchema],
    ):
        next_current_db_item = []

        for parent_db_item in parent_db_items:
            new_next_items = cls.process_single_db_item_and_prepare_includes(
                parent_db_item=parent_db_item,
                included_objects=included_objects,
            )
            next_current_db_item.extend(new_next_items)
        return next_current_db_item

    def process_include_with_nested(
        self,
        include: str,
        current_db_item: Union[List[TypeModel], TypeModel],
        item_as_schema: TypeSchema,
        current_relation_schema: Type[TypeSchema],
    ) -> Tuple[Dict[str, TypeSchema], List[JSONAPIObjectSchema]]:
        root_item_key = (item_as_schema.id, item_as_schema.type)
        included_objects: Dict[Tuple[str, str], TypeSchema] = {
            root_item_key: item_as_schema,
        }
        previous_resource_type = item_as_schema.type

        for related_field_name in include.split(SPLIT_REL):
            object_schemas = self.jsonapi.schema_builder.create_jsonapi_object_schemas(
                schema=current_relation_schema,
                includes=[related_field_name],
                compute_included_schemas=bool([related_field_name]),
            )
            relationships_schema = object_schemas.relationships_schema
            schemas_include = object_schemas.can_be_included_schemas

            current_relation_field: ModelField = current_relation_schema.__fields__[related_field_name]
            current_relation_schema: Type[TypeSchema] = current_relation_field.type_

            relationship_info: RelationshipInfo = current_relation_field.field_info.extra["relationship"]
            included_object_schema: Type[JSONAPIObjectSchema] = schemas_include[related_field_name]

            if not isinstance(current_db_item, Iterable):
                # xxx: less if/else
                current_db_item = [current_db_item]

            # ctx vars to skip multi-level args passing
            relationships_schema_ctx_var.set(relationships_schema)
            object_schema_ctx_var.set(object_schemas.object_jsonapi_schema)
            previous_resource_type_ctx_var.set(previous_resource_type)
            related_field_name_ctx_var.set(related_field_name)
            relationship_info_ctx_var.set(relationship_info)
            included_object_schema_ctx_var.set(included_object_schema)

            current_db_item = self.process_db_items_and_prepare_includes(
                parent_db_items=current_db_item,
                included_objects=included_objects,
            )

            previous_resource_type = relationship_info.resource_type

        return included_objects.pop(root_item_key), list(included_objects.values())

    def process_db_object(
        self,
        includes: List[str],
        item: TypeModel,
        item_schema: Type[TypeSchema],
        object_schemas: JSONAPIObjectSchemas,
    ):
        included_objects = []

        item_as_schema = object_schemas.object_jsonapi_schema(
            id=self.get_db_item_id(item),
            attributes=object_schemas.attributes_schema.from_orm(item),
        )

        for include in includes:
            item_as_schema, new_included_objects = self.process_include_with_nested(
                include=include,
                current_db_item=item,
                item_as_schema=item_as_schema,
                current_relation_schema=item_schema,
            )

            included_objects.extend(new_included_objects)

        return item_as_schema, included_objects

    def process_includes_for_db_items(
        self,
        includes: List[str],
        items_from_db: List[TypeModel],
        item_schema: Type[TypeSchema],
    ):
        object_schemas = self.jsonapi.schema_builder.create_jsonapi_object_schemas(
            schema=item_schema,
            includes=includes,
            compute_included_schemas=bool(includes),
            use_schema_cache=False,
        )

        result_objects = []
        # form:
        # `(type, id): serialized_object`
        # helps to exclude duplicates
        included_objects: Dict[Tuple[str, str], TypeSchema] = {}
        for item in items_from_db:
            jsonapi_object, new_included = self.process_db_object(
                includes=includes,
                item=item,
                item_schema=item_schema,
                object_schemas=object_schemas,
            )
            result_objects.append(jsonapi_object)
            for included in new_included:
                # update too?
                included_objects[(included.type, included.id)] = included

        extras = {}
        if includes:
            # if query has includes, add includes to response
            # even if no related objects were found
            extras.update(
                included=[
                    # ignore key
                    value
                    # sort for prettiness
                    for key, value in sorted(included_objects.items())
                ],
            )

        return result_objects, object_schemas, extras
