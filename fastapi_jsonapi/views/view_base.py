import logging
from functools import partial
from typing import (
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
    Type,
    Union,
)

from pydantic.fields import ModelField

from fastapi_jsonapi import QueryStringManager, RoutersJSONAPI, SqlalchemyEngine
from fastapi_jsonapi.api import JSONAPIObjectSchemas
from fastapi_jsonapi.data_layers.data_typing import (
    TypeModel,
    TypeSchema,
)
from fastapi_jsonapi.schema import (
    JSONAPIObjectSchema,
    JSONAPIResultDetailSchema,
    get_related_schema,
)
from fastapi_jsonapi.schema_base import BaseModel, RelationshipInfo
from fastapi_jsonapi.splitter import SPLIT_REL

logger = logging.getLogger(__name__)


class ViewBase:
    def __init__(self, jsonapi: RoutersJSONAPI, **options):
        self.jsonapi = jsonapi
        self.options = options

    @classmethod
    def prepare_related_object_data(
        cls,
        item_from_db: TypeModel,
        included_object_schema: Type[TypeSchema],
        relationship_info: RelationshipInfo,
    ) -> Tuple[Dict[str, Union[str, int]], Optional[TypeSchema]]:
        item_id = str(item_from_db.id)
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
        relationship_info: RelationshipInfo,
        included_object_schema: Type[TypeSchema],
    ) -> Tuple[Optional[Dict[str, Union[str, int]]], List[TypeSchema]]:
        prepare_related_db_item = partial(
            cls.prepare_related_object_data,
            included_object_schema=included_object_schema,
            relationship_info=relationship_info,
        )

        included_objects = []
        if isinstance(related_db_item, Iterable):
            data_for_relationship = []
            for included_item in related_db_item:
                relation_data, processed_object = prepare_related_db_item(
                    item_from_db=included_item,
                )
                data_for_relationship.append(relation_data)
                if processed_object:
                    included_objects.append(processed_object)
        else:
            if related_db_item is None:
                return None, included_objects

            data_for_relationship, processed_object = prepare_related_db_item(
                item_from_db=related_db_item,
            )
            if processed_object:
                included_objects.append(processed_object)
        return data_for_relationship, included_objects

    @classmethod
    def update_related_object(
        cls,
        relationship_data: Union[Dict[str, str], List[Dict[str, str]]],
        relationships_schema: Type[BaseModel],
        object_schema: Type[JSONAPIObjectSchema],
        included_objects: Dict[Tuple[str, str], TypeSchema],
        cache_key: Tuple[str, str],
        related_field_name: str,
    ):
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
            # TODO: when including 'user.bio', it loads user AND user's bio.
            #  need to load only bio when includes 'user.bio' (but how)

            object_schemas = self.jsonapi.create_jsonapi_object_schemas(
                schema=current_relation_schema,
                includes=[related_field_name],
                compute_included_schemas=bool([related_field_name]),
            )
            relationships_schema = object_schemas.relationships_schema
            schemas_include = object_schemas.can_be_included_schemas

            current_relation_field: ModelField = current_relation_schema.__fields__[related_field_name]
            current_relation_schema: Type[TypeSchema] = current_relation_field.type_

            relationship_info: RelationshipInfo = current_relation_field.field_info.extra["relationship"]
            included_object_schema = schemas_include[related_field_name]

            process_db_item = partial(
                self.prepare_data_for_relationship,
                relationship_info=relationship_info,
                included_object_schema=included_object_schema,
            )

            if isinstance(current_db_item, Iterable):
                for parent_db_item in current_db_item:
                    cache_key = (str(parent_db_item.id), previous_resource_type)
                    current_db_item = getattr(parent_db_item, related_field_name)
                    if isinstance(current_db_item, Iterable):
                        relationship_data_items = []

                        for db_item in current_db_item:
                            data_for_relationship, new_included = process_db_item(
                                related_db_item=db_item,
                            )
                            relationship_data_items.append(data_for_relationship)

                            for included in new_included:
                                included_objects[(included.id, included.type)] = included

                        self.update_related_object(
                            relationship_data=relationship_data_items,
                            relationships_schema=relationships_schema,
                            object_schema=object_schemas.object_jsonapi_schema,
                            included_objects=included_objects,
                            cache_key=cache_key,
                            related_field_name=related_field_name,
                        )
                    else:
                        data_for_relationship, new_included = process_db_item(
                            related_db_item=current_db_item,
                        )

                        for included in new_included:
                            included_objects[(included.id, included.type)] = included

                        self.update_related_object(
                            relationship_data=data_for_relationship,
                            relationships_schema=relationships_schema,
                            object_schema=object_schemas.object_jsonapi_schema,
                            included_objects=included_objects,
                            cache_key=cache_key,
                            related_field_name=related_field_name,
                        )

            else:
                parent_db_item = current_db_item
                cache_key = (str(parent_db_item.id), previous_resource_type)
                current_db_item = getattr(parent_db_item, related_field_name)
                if isinstance(current_db_item, Iterable):
                    relationship_data_items = []

                    for db_item in current_db_item:
                        data_for_relationship, new_included = process_db_item(
                            related_db_item=db_item,
                        )
                        relationship_data_items.append(data_for_relationship)

                        for included in new_included:
                            included_objects[(included.id, included.type)] = included

                    self.update_related_object(
                        relationship_data=relationship_data_items,
                        relationships_schema=relationships_schema,
                        object_schema=object_schemas.object_jsonapi_schema,
                        included_objects=included_objects,
                        cache_key=cache_key,
                        related_field_name=related_field_name,
                    )
                else:
                    data_for_relationship, new_included = process_db_item(
                        related_db_item=current_db_item,
                    )

                    for included in new_included:
                        included_objects[(included.id, included.type)] = included

                    self.update_related_object(
                        relationship_data=data_for_relationship,
                        relationships_schema=relationships_schema,
                        object_schema=object_schemas.object_jsonapi_schema,
                        included_objects=included_objects,
                        cache_key=cache_key,
                        related_field_name=related_field_name,
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
            id=str(item.id),  # TODO: error if None?
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
        object_schemas = self.jsonapi.create_jsonapi_object_schemas(
            schema=item_schema,
            includes=includes,
            compute_included_schemas=bool(includes),
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

    async def get_detailed_result(
        self,
        dl: SqlalchemyEngine,
        view_kwargs: Dict[str, Union[str, int]],
        query_params: QueryStringManager = None,
        schema: Type[TypeSchema] = None,
    ) -> JSONAPIResultDetailSchema:
        # todo: generate dl?
        db_object = await dl.get_object(view_kwargs=view_kwargs, qs=query_params)

        result_objects, object_schemas, extras = self.process_includes_for_db_items(
            includes=query_params.include,
            items_from_db=[db_object],
            item_schema=schema or self.jsonapi.schema_detail,
        )
        # todo: is it ok to do through list?
        result_object = result_objects[0]

        # we need to build a new schema here
        # because we'd like to exclude some fields (relationships, includes, etc)
        detail_jsonapi_schema = self.jsonapi.build_schema_for_detail_result(
            name=f"Result{self.__class__.__name__}",
            object_jsonapi_schema=object_schemas.object_jsonapi_schema,
            includes_schemas=object_schemas.included_schemas_list,
        )
        return detail_jsonapi_schema(
            data=result_object,
            **extras,
        )
