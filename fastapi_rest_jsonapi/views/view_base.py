import logging

from fastapi_rest_jsonapi import RoutersJSONAPI

from typing import Type, Iterable, Set, Tuple, Union, Dict, List

from fastapi_rest_jsonapi.api import JSONAPIObjectSchemas
from fastapi_rest_jsonapi.data_layers.data_typing import (
    TypeModel,
    TypeSchema,
)
from fastapi_rest_jsonapi.schema import (
    JSONAPIObjectSchema,
)

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
    ):
        data_for_relationship = dict(id=item_from_db.id)
        key = (item_from_db.id, relationship_info.resource_type)
        processed_object = None
        if key not in known_included:
            processed_object = included_object_schema(
                id=item_from_db.id,
                attributes=item_from_db,
                type=relationship_info.resource_type,
            )
            known_included.add(key)

        return data_for_relationship, processed_object

    def prepare_data_for_relationship(
        self,
        current_db_item: TypeModel,
        current_schema: Type[TypeSchema],
        related_field_name: str,
        schemas_include: Dict[str, Type[JSONAPIObjectSchema]],
        known_included: Set[Tuple[Union[int, str], str]],
    ):
        relationship_info: RelationshipInfo = current_schema.__fields__[related_field_name].field_info.extra[
            "relationship"
        ]
        relationship_db_data = getattr(current_db_item, related_field_name)
        included_object_schema = schemas_include[related_field_name]

        def prepare_related_db_item(item_from_db: TypeModel):
            return self.prepare_related_object_data(
                item_from_db=item_from_db,
                included_object_schema=included_object_schema,
                relationship_info=relationship_info,
                known_included=known_included,
            )

        included_objects = []
        if isinstance(relationship_db_data, Iterable):
            data_for_relationship = []
            for included_item in relationship_db_data:
                relation_data, processed_object = prepare_related_db_item(
                    item_from_db=included_item,
                )
                data_for_relationship.append(relation_data)
                if processed_object:
                    included_objects.append(processed_object)
        else:
            data_for_relationship, processed_object = prepare_related_db_item(
                item_from_db=relationship_db_data,
            )
            if processed_object:
                included_objects.append(processed_object)

        return data_for_relationship, included_objects

    def process_one_include_with_nested(
        self,
        include: str,
        current_db_item: TypeModel,
        current_schema: Type[TypeSchema],
        relationships_schema: Type[TypeSchema],
        schemas_include: Dict[str, Type[JSONAPIObjectSchema]],
        known_included: Set[Tuple[Union[int, str], str]],
    ):
        top_level_relationships = {}
        included_objects = []
        top_level_include = True
        for related_field_name in include.split(SPLIT_REL):

            # I'm really sorry about it, but it's the shortest way
            # otherwise I'll have to return these schemas separately
            relationship_data_schema = relationships_schema.__fields__[related_field_name].type_
            # relationship_data_schema = get_related_schema(object_schemas.relationships_schema, include)

            data_for_relationship, new_included = self.prepare_data_for_relationship(
                current_db_item=current_db_item,
                current_schema=current_schema,
                related_field_name=related_field_name,
                schemas_include=schemas_include,
                known_included=known_included,
            )
            included_objects.extend(new_included)

            # TODO: PROCESS LEVELS 2+ !!
            if top_level_include:
                top_level_relationships[related_field_name] = relationship_data_schema(data=data_for_relationship)
                top_level_include = False

        return top_level_relationships, included_objects

    def process_db_object(
        self,
        includes: List[str],
        item: TypeModel,
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
                current_schema=self.jsonapi.model_schema,
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

    def process_includes_for_db_items(self, includes: List[str], items_from_db: List[TypeModel]):
        object_schemas = self.jsonapi.create_jsonapi_object_schemas(
            schema=self.jsonapi.model_schema,
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

        return result_objects, extras
