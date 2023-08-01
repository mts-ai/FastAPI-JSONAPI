"""JSON API schemas builder class."""
from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)

import pydantic
from pydantic import BaseConfig
from pydantic import BaseModel as PydanticBaseModel
from pydantic.fields import ModelField

from fastapi_jsonapi.data_layers.data_typing import TypeSchema
from fastapi_jsonapi.schema import (
    BaseJSONAPIDataInSchema,
    BaseJSONAPIItemInSchema,
    BaseJSONAPIRelationshipDataToManySchema,
    BaseJSONAPIRelationshipDataToOneSchema,
    BaseJSONAPIRelationshipSchema,
    BaseJSONAPIResultSchema,
    JSONAPIObjectSchema,
    JSONAPIResultDetailSchema,
    JSONAPIResultListSchema,
    RelationshipInfoSchema,
)
from fastapi_jsonapi.schema_base import BaseModel, Field, RelationshipInfo, registry
from fastapi_jsonapi.splitter import SPLIT_REL

JSON_API_RESPONSE_TYPE = Dict[Union[int, str], Dict[str, Any]]

JSONAPIObjectSchemaType = TypeVar("JSONAPIObjectSchemaType", bound=PydanticBaseModel)

not_passed = object()


# todo: when 3.9 support is dropped, return back `slots=True to JSONAPIObjectSchemas dataclass`


@dataclass(frozen=True)
class JSONAPIObjectSchemas:
    attributes_schema: Type[BaseModel]
    relationships_schema: Type[BaseModel]
    object_jsonapi_schema: Type[JSONAPIObjectSchema]
    can_be_included_schemas: Dict[str, Type[JSONAPIObjectSchema]]

    @property
    def included_schemas_list(self) -> List[Type[JSONAPIObjectSchema]]:
        return list(self.can_be_included_schemas.values())


@dataclass(frozen=True)
class BuiltSchemasDTO:
    schema_in_post: Type[BaseJSONAPIDataInSchema]
    schema_in_patch: Type[BaseJSONAPIDataInSchema]
    detail_response_schema: Type[JSONAPIResultDetailSchema]
    list_response_schema: Type[JSONAPIResultListSchema]


class SchemaBuilder:
    # IDK if there's a better way than global caches
    # shared between ALL RoutersJSONAPI instances
    object_schemas_cache = {}
    relationship_schema_cache = {}
    base_jsonapi_object_schemas_cache = {}

    def __init__(
        self,
        resource_type: str,
    ):
        self._resource_type = resource_type

    def _create_schemas_objects_list(self, schema: Type[BaseModel]) -> Type[JSONAPIResultListSchema]:
        object_jsonapi_list_schema, list_jsonapi_schema = self.build_list_schemas(schema)
        # TODO: do we need this `object_jsonapi_list_schema` field? it's not used anywhere 🤔
        # self.object_jsonapi_list_schema: Type[JSONAPIObjectSchema] = object_jsonapi_list_schema
        return list_jsonapi_schema

    def _create_schemas_object_detail(self, schema: Type[BaseModel]) -> Type[JSONAPIResultDetailSchema]:
        object_jsonapi_detail_schema, detail_jsonapi_schema = self.build_detail_schemas(schema)
        # TODO: do we need this `object_jsonapi_detail_schema` field? it's not used anywhere 🤔
        # self.object_jsonapi_detail_schema: Type[JSONAPIObjectSchema] = object_jsonapi_detail_schema

        return detail_jsonapi_schema

    def create_schemas(
        self,
        schema: Type[BaseModel],
        schema_in_post: Optional[Type[BaseModel]] = None,
        schema_in_patch: Optional[Type[BaseModel]] = None,
    ) -> BuiltSchemasDTO:
        # TODO: generic?
        schema_name_in_post_suffix = "InPost"
        schema_in_post = schema_in_post or schema

        schema_name_in_patch_suffix = "InPatch"
        schema_in_patch = schema_in_patch or schema

        schemas_in_post = self.build_schema_in(
            schema_in=schema_in_post,
            schema_name_suffix=schema_name_in_post_suffix,
        )

        schemas_in_patch = self.build_schema_in(
            schema_in=schema_in_patch,
            schema_name_suffix=schema_name_in_patch_suffix,
        )

        return BuiltSchemasDTO(
            schema_in_post=schemas_in_post,
            schema_in_patch=schemas_in_patch,
            list_response_schema=self._create_schemas_objects_list(schema),
            detail_response_schema=self._create_schemas_object_detail(schema),
        )

    def build_schema_in(
        self,
        schema_in: Type[BaseModel],
        schema_name_suffix: str = "",
    ) -> Type[BaseJSONAPIDataInSchema]:
        base_schema_name = schema_in.__name__.removesuffix("Schema") + schema_name_suffix

        (
            # pre-built attributed
            attributes_schema,
            # relationships
            relationships_schema,
            # anything that can be included
            included_schemas,
        ) = self._get_info_from_schema_for_building(
            base_name=base_schema_name,
            schema=schema_in,
        )

        object_jsonapi_schema = self._build_jsonapi_object(
            base_name=base_schema_name,
            resource_type=self._resource_type,
            attributes_schema=attributes_schema,
            relationships_schema=relationships_schema,
            includes=not_passed,
            model_base=BaseJSONAPIItemInSchema,
        )

        wrapped_object_jsonapi_schema = pydantic.create_model(
            f"{base_schema_name}ObjectDataJSONAPI",
            data=(object_jsonapi_schema, ...),
            __base__=BaseJSONAPIDataInSchema,
        )

        return wrapped_object_jsonapi_schema

    def _build_schema(
        self,
        base_name: str,
        schema: Type[BaseModel],
        builder: Callable,
        includes: Iterable[str] = not_passed,
    ):
        object_schemas = self.create_jsonapi_object_schemas(
            schema=schema,
            base_name=base_name,
            compute_included_schemas=True,
            includes=includes,
        )
        object_jsonapi_schema = object_schemas.object_jsonapi_schema
        response_jsonapi_schema = builder(
            name=base_name,
            object_jsonapi_schema=object_jsonapi_schema,
            includes_schemas=object_schemas.included_schemas_list,
        )
        return object_jsonapi_schema, response_jsonapi_schema

    def build_detail_schemas(
        self,
        schema: Type[BaseModel],
        includes: Iterable[str] = not_passed,
    ) -> Tuple[Type[JSONAPIObjectSchema], Type[JSONAPIResultDetailSchema]]:
        return self._build_schema(
            base_name=f"{schema.__name__}Detail",
            schema=schema,
            builder=self.build_schema_for_detail_result,
            includes=includes,
        )

    def build_list_schemas(
        self,
        schema: Type[BaseModel],
        includes: Iterable[str] = not_passed,
    ) -> Tuple[Type[JSONAPIObjectSchema], Type[JSONAPIResultListSchema]]:
        return self._build_schema(
            base_name=f"{schema.__name__}List",
            schema=schema,
            builder=self.build_schema_for_list_result,
            includes=includes,
        )

    def _get_info_from_schema_for_building(
        self,
        base_name: str,
        schema: Type[BaseModel],
        includes: Iterable[str] = not_passed,
    ) -> Tuple[Type[BaseModel], Type[BaseModel], List[Tuple[str, BaseModel, str]]]:
        attributes_schema_fields = {}
        relationships_schema_fields = {}
        included_schemas: List[Tuple[str, BaseModel, str]] = []
        for name, field in (schema.__fields__ or {}).items():
            if isinstance(field.field_info.extra.get("relationship"), RelationshipInfo):
                if includes is not_passed:
                    pass
                elif name not in includes:
                    # if includes are passed, skip this if name not present!
                    continue
                relationship: RelationshipInfo = field.field_info.extra["relationship"]
                relationship_schema = self.create_relationship_data_schema(
                    field_name=name,
                    base_name=base_name,
                    field=field,
                    relationship_info=relationship,
                )
                relationships_schema_fields[name] = (relationship_schema, None)  # allow to not pass relationships
                # works both for to-one and to-many
                included_schemas.append((name, field.type_, relationship.resource_type))
            elif name == "id":
                # skip id field (should be on top)
                continue
            else:
                attributes_schema_fields[name] = (field.outer_type_, field.field_info)

        class ConfigOrmMode(BaseConfig):
            orm_mode = True

        attributes_schema = pydantic.create_model(
            f"{base_name}AttributesJSONAPI",
            **attributes_schema_fields,
            __config__=ConfigOrmMode,
        )

        relationships_schema = pydantic.create_model(
            f"{base_name}RelationshipsJSONAPI",
            **relationships_schema_fields,
            __config__=ConfigOrmMode,
        )

        return attributes_schema, relationships_schema, included_schemas

    def create_relationship_schema(
        self,
        name: str,
        relationship_info: RelationshipInfo,
    ) -> Type[BaseJSONAPIRelationshipSchema]:
        # TODO: cache?
        if name.endswith("s"):
            # plural to single
            name = name[:-1]

        schema_name = f"{name}RelationshipJSONAPI".format(name=name)
        relationship_schema = pydantic.create_model(
            schema_name,
            id=(str, Field(..., description="Resource object id", example=relationship_info.resource_id_example)),
            type=(str, Field(default=relationship_info.resource_type, description="Resource type")),
            __base__=BaseJSONAPIRelationshipSchema,
        )

        return relationship_schema

    def create_relationship_data_schema(
        self,
        field_name: str,
        base_name: str,
        field: ModelField,
        relationship_info: RelationshipInfo,
    ) -> RelationshipInfoSchema:
        cache_key = (base_name, field_name, relationship_info.resource_type, relationship_info.many)
        if cache_key in self.relationship_schema_cache:
            return self.relationship_schema_cache[cache_key]

        base_name = base_name.removesuffix("Schema")
        schema_name = f"{base_name}{field_name.title()}"
        relationship_schema = self.create_relationship_schema(
            name=schema_name,
            relationship_info=relationship_info,
        )
        base = BaseJSONAPIRelationshipDataToOneSchema
        if relationship_info.many:
            relationship_schema = List[relationship_schema]
            base = BaseJSONAPIRelationshipDataToManySchema

        relationship_data_schema = pydantic.create_model(
            f"{schema_name}RelationshipDataJSONAPI",
            # TODO: on create (post request) sometimes it's required and at the same time on fetch it's not required
            data=(relationship_schema, Field(... if field.required else None)),
            __base__=base,
        )
        self.relationship_schema_cache[cache_key] = relationship_data_schema
        return relationship_data_schema

    def _build_jsonapi_object(
        self,
        base_name: str,
        resource_type: str,
        attributes_schema: Type[TypeSchema],
        relationships_schema: Type[TypeSchema],
        includes,
        model_base: Type[JSONAPIObjectSchemaType] = JSONAPIObjectSchema,
    ) -> Type[JSONAPIObjectSchemaType]:
        if base_name in self.base_jsonapi_object_schemas_cache:
            return self.base_jsonapi_object_schemas_cache[base_name]
        object_jsonapi_schema_fields = {
            "attributes": (attributes_schema, ...),
        }
        if includes:
            object_jsonapi_schema_fields.update(
                relationships=(relationships_schema, None),  # allow None
            )

        object_jsonapi_schema = pydantic.create_model(
            f"{base_name}ObjectJSONAPI",
            **object_jsonapi_schema_fields,
            type=(str, Field(default=resource_type or self._resource_type, description="Resource type")),
            __base__=model_base,
        )
        self.base_jsonapi_object_schemas_cache[base_name] = object_jsonapi_schema

        return object_jsonapi_schema

    def find_all_included_schemas(
        self,
        schema: Type[BaseModel],
        resource_type: str,
        includes: Iterable[str],
        included_schemas: List[Tuple[str, BaseModel, str]],
    ) -> Dict[str, Type[JSONAPIObjectSchema]]:
        if includes is not_passed:
            return {
                # prepare same object schema
                # TODO: caches?!
                name: self.create_jsonapi_object_schemas(
                    included_schema,
                    resource_type=resource_type,
                ).object_jsonapi_schema
                for (name, included_schema, resource_type) in included_schemas
            }

        can_be_included_schemas = {}
        for i_include in includes:
            current_schema = schema
            relations_list: List[str] = i_include.split(SPLIT_REL)
            for part_index, include_part in enumerate(relations_list, start=1):
                # find nested from the Schema
                nested_schema: Type[BaseModel] = current_schema.__fields__[include_part].type_
                # find all relations for this one
                nested_schema_includes = set(relations_list[: part_index - 1] + relations_list[part_index:])
                related_jsonapi_object_schema = self.create_jsonapi_object_schemas(
                    nested_schema,
                    resource_type=resource_type,
                    # higher and lower
                    includes=nested_schema_includes,
                ).object_jsonapi_schema
                # cache it
                can_be_included_schemas[include_part] = related_jsonapi_object_schema
                # prepare for the next step
                current_schema = nested_schema

        return can_be_included_schemas

    def create_jsonapi_object_schemas(
        self,
        schema: Type[BaseModel],
        includes: Iterable[str] = not_passed,
        resource_type: str = None,
        base_name: str = "",
        compute_included_schemas: bool = False,
    ) -> JSONAPIObjectSchemas:
        if schema in self.object_schemas_cache and includes is not_passed:
            return self.object_schemas_cache[schema]

        schema.update_forward_refs(**registry.schemas)
        base_name = base_name or schema.__name__

        if includes is not not_passed:
            includes = set(includes)

        (
            # pre-built attributed
            attributes_schema,
            # relationships
            relationships_schema,
            # anything that can be included
            included_schemas,
        ) = self._get_info_from_schema_for_building(
            base_name=base_name,
            schema=schema,
            includes=includes,
        )

        object_jsonapi_schema = self._build_jsonapi_object(
            base_name=base_name,
            resource_type=resource_type,
            attributes_schema=attributes_schema,
            relationships_schema=relationships_schema,
            includes=includes,
        )

        can_be_included_schemas = {}
        if compute_included_schemas:
            can_be_included_schemas = self.find_all_included_schemas(
                schema=schema,
                resource_type=resource_type,
                includes=includes,
                included_schemas=included_schemas,
            )

        result = JSONAPIObjectSchemas(
            attributes_schema=attributes_schema,
            relationships_schema=relationships_schema,
            object_jsonapi_schema=object_jsonapi_schema,
            can_be_included_schemas=can_be_included_schemas,
        )
        if includes is not_passed:
            self.object_schemas_cache[schema] = result
        return result

    def build_schema_for_list_result(
        self,
        name: str,
        object_jsonapi_schema: Type[JSONAPIObjectSchema],
        includes_schemas: List[Type[JSONAPIObjectSchema]],
    ) -> Type[JSONAPIResultListSchema]:
        return self.build_schema_for_result(
            name=f"{name}JSONAPI",
            base=JSONAPIResultListSchema,
            data_type=List[object_jsonapi_schema],
            includes_schemas=includes_schemas,
        )

    def build_schema_for_detail_result(
        self,
        name: str,
        object_jsonapi_schema: Type[JSONAPIObjectSchema],
        includes_schemas: List[Type[JSONAPIObjectSchema]],
    ) -> Type[JSONAPIResultDetailSchema]:
        # return detail_jsonapi_schema
        return self.build_schema_for_result(
            name=f"{name}JSONAPI",
            base=JSONAPIResultDetailSchema,
            data_type=object_jsonapi_schema,
            includes_schemas=includes_schemas,
        )

    def build_schema_for_result(
        self,
        name: str,
        base: Type[BaseJSONAPIResultSchema],
        data_type: Union[Type[JSONAPIObjectSchema], Type[List[JSONAPIObjectSchema]]],
        includes_schemas: List[Type[JSONAPIObjectSchema]],
    ) -> Union[Type[JSONAPIResultListSchema], Type[JSONAPIResultDetailSchema]]:
        included_schema_annotation = Union[JSONAPIObjectSchema]
        for includes_schema in includes_schemas:
            included_schema_annotation = Union[included_schema_annotation, includes_schema]

        schema_fields = {
            "data": (data_type, ...),
        }
        if includes_schemas:
            schema_fields.update(
                included=(
                    List[included_schema_annotation],
                    Field(None),
                ),
            )

        result_jsonapi_schema = pydantic.create_model(
            name,
            **schema_fields,
            __base__=base,
        )
        return result_jsonapi_schema
