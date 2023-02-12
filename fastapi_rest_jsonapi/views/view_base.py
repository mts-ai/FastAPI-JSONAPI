import logging

from pydantic.fields import ModelField

from fastapi_rest_jsonapi import RoutersJSONAPI

from typing import Type, Iterable, Set, Tuple, Union, Dict, List, Optional

from fastapi_rest_jsonapi.api import JSONAPIObjectSchemas
from fastapi_rest_jsonapi.data_layers.data_typing import (
    TypeModel,
    TypeSchema,
)
from fastapi_rest_jsonapi.schema import (
    JSONAPIObjectSchema,
    get_related_schema,
)

from fastapi_rest_jsonapi import SqlalchemyEngine, QueryStringManager
from fastapi_rest_jsonapi.schema import JSONAPIResultDetailSchema


from fastapi_rest_jsonapi.schema_base import RelationshipInfo
from fastapi_rest_jsonapi.splitter import SPLIT_REL


logger = logging.getLogger(__name__)


class ViewBase:
    def __init__(self, jsonapi: RoutersJSONAPI, **options):
        self.jsonapi = jsonapi
        self.options = options

    def prepare_related_object_data(
        self,
        item_from_db: TypeModel,
        included_object_schema: Type[TypeSchema],
        relationship_info: RelationshipInfo,
        known_included: Set[Tuple[Union[int, str], str]],
    ) -> Tuple[Dict[str, Union[str, int]], Optional[TypeSchema]]:
        item_id = str(item_from_db.id)
        data_for_relationship = dict(id=item_id)
        key = (item_id, relationship_info.resource_type)
        processed_object = None
        if key not in known_included:
            processed_object = included_object_schema(
                id=item_id,
                attributes=item_from_db,
                type=relationship_info.resource_type,
            )
            known_included.add(key)

        return data_for_relationship, processed_object

    def prepare_data_for_relationship(
        self,
        related_db_item: Union[List[TypeModel], TypeModel],
        relationship_info: RelationshipInfo,
        included_object_schema: Type[TypeSchema],
        known_included: Set[Tuple[Union[int, str], str]],
    ) -> Tuple[Optional[Dict[str, Union[str, int]]], List[TypeSchema],]:
        def prepare_related_db_item(item_from_db: TypeModel) -> Tuple[Dict[str, Union[str, int]], Optional[TypeSchema]]:
            return self.prepare_related_object_data(
                item_from_db=item_from_db,
                included_object_schema=included_object_schema,
                relationship_info=relationship_info,
                known_included=known_included,
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

    def process_one_include_with_nested(
        self,
        include: str,
        current_db_item: TypeModel,
        current_relation_schema: Type[TypeSchema],
        relationships_schema: Type[TypeSchema],
        schemas_include: Dict[str, Type[JSONAPIObjectSchema]],
        known_included: Set[Tuple[Union[int, str], str]],
    ) -> Tuple[Dict[str, TypeSchema], List[JSONAPIObjectSchema]]:
        top_level_relationships = {}
        included_objects = []
        previous_included = []
        previous_include_key = None
        previous_relationship_info = None
        top_level_include = True
        for related_field_name in include.split(SPLIT_REL):
            # TODO: when including 'user.bio', it loads user AND user's bio.
            #  need to load only bio when includes 'user.bio'
            current_relation_field: ModelField = current_relation_schema.__fields__[related_field_name]
            current_relation_schema: Type[TypeSchema] = current_relation_field.type_
            parent_db_item: Union[List[TypeModel], TypeModel] = current_db_item
            current_db_item: Union[List[TypeModel], TypeModel] = getattr(current_db_item, related_field_name)
            relationship_info: RelationshipInfo = current_relation_field.field_info.extra["relationship"]
            included_object_schema = schemas_include[related_field_name]

            data_for_relationship, new_included = self.prepare_data_for_relationship(
                related_db_item=current_db_item,
                relationship_info=relationship_info,
                included_object_schema=included_object_schema,
                known_included=known_included,
            )
            if previous_include_key:
                for prev_included_item in previous_included:
                    fwd_relationships_schema = get_related_schema(prev_included_item.__class__, "relationships")
                    fwd_relationship_data_schema = get_related_schema(
                        fwd_relationships_schema,
                        previous_include_key,
                    )
                    # TODO!! xxx
                    #  this will overwrite any existing data
                    #  due to 'known includes' some items may be not filled :(
                    #  idea: use dict instead of set for known and update those
                    prev_included_item.relationships = fwd_relationship_data_schema(data=data_for_relationship)

                for new_included_item in new_included:
                    reverse_relationships_schema = get_related_schema(new_included_item.__class__, "relationships")
                    reverse_relationship_data_schema = get_related_schema(
                        reverse_relationships_schema,
                        previous_include_key,
                    )
                    # reverse_relationship_data, _ =
                    data = dict(id=parent_db_item.id)
                    if relationship_info.many:
                        data = [data]
                    # TODO!! xxx
                    #  this will overwrite any existing data
                    new_included_item.relationships = reverse_relationship_data_schema(data=data)

            previous_include_key = related_field_name
            previous_included = new_included
            previous_relationship_info = relationship_info

            included_objects.extend(new_included)

            # TODO: level 2+ not finished yet (relationship stays null)
            if top_level_include:
                relationship_data_schema = get_related_schema(relationships_schema, related_field_name)
                top_level_relationships[related_field_name] = relationship_data_schema(data=data_for_relationship)
                top_level_include = False

        return top_level_relationships, included_objects

    def process_db_object(
        self,
        includes: List[str],
        item: TypeModel,
        item_schema: Type[TypeSchema],
        object_schemas: JSONAPIObjectSchemas,
        known_included: Set[Tuple[Union[int, str], str]],
    ):
        included_objects = []

        schema_kwargs = dict(
            id=item.id,
            attributes=object_schemas.attributes_schema.from_orm(item),
        )

        obj_relationships = {}
        for include in includes:
            top_level_relationships, new_included_objects = self.process_one_include_with_nested(
                include=include,
                current_db_item=item,
                current_relation_schema=item_schema,
                relationships_schema=object_schemas.relationships_schema,
                schemas_include=object_schemas.can_be_included_schemas,
                known_included=known_included,
            )

            obj_relationships.update(top_level_relationships)
            included_objects.extend(new_included_objects)

        if obj_relationships:
            relationships = object_schemas.relationships_schema(**obj_relationships)
            schema_kwargs.update(
                relationships=relationships,
            )

        item_as_schema = object_schemas.object_jsonapi_schema(**schema_kwargs)

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
        included_objects = []
        known_included = set()
        for item in items_from_db:
            jsonapi_object, new_included = self.process_db_object(
                includes=includes,
                item=item,
                item_schema=item_schema,
                object_schemas=object_schemas,
                known_included=known_included,
            )
            result_objects.append(jsonapi_object)
            included_objects.extend(new_included)

        extras = {}
        if includes:
            # if query has includes, add includes to response
            # even if no related objects were found
            extras.update(included=included_objects)

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
            includes_schemas=list(object_schemas.can_be_included_schemas.values()),
        )
        return detail_jsonapi_schema(
            data=result_object,
            **extras,
        )
