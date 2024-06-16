"""JSON API schemas builder class."""

from __future__ import annotations

import logging
from dataclasses import (
    dataclass,
    field as dataclass_field,
)
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Callable,
    ClassVar,
    TypeVar,
    Union,
)

import pydantic
from pydantic import (
    BaseModel as PydanticBaseModel,
    BeforeValidator,
    AfterValidator,
)
from pydantic import ConfigDict

from fastapi_jsonapi.common import (
    get_relationship_info_from_field_metadata,
    search_client_can_set_id,
)
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
    get_schema_from_field_annotation,
)
from fastapi_jsonapi.schema_base import (
    BaseModel,
    Field,
    registry,
)
from fastapi_jsonapi.splitter import SPLIT_REL
from fastapi_jsonapi.types_metadata import ClientCanSetId, RelationshipInfo
from fastapi_jsonapi.validation_utils import (
    extract_field_validators,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from pydantic.fields import FieldInfo

    from fastapi_jsonapi.data_typing import TypeSchema

JSON_API_RESPONSE_TYPE = dict[int | str, dict[str, Any]]

JSONAPIObjectSchemaType = TypeVar("JSONAPIObjectSchemaType", bound=PydanticBaseModel)

not_passed = object()

log = logging.getLogger(__name__)


# TODO: check in runtime and update dataclass kwargs (slots)
# TODO: when 3.9 support is dropped, return back `slots=True to JSONAPIObjectSchemas dataclass`


class FieldConfig:
    cast_type: Callable

    def __init__(self, cast_type: Callable | None = None):
        self.cast_type = cast_type


class TransferSaveWrapper:
    """
    This class helps to transfer type from one pydantic Field to another

    Types doesn't allowed to be passed as keywords to pydantic Field,
    so this exists to help save them

    In other case OpenAPI generation will fail
    """

    def __init__(self, field_config: FieldConfig):
        def get_field_config() -> FieldConfig:
            return field_config

        self.get_field_config = get_field_config


@dataclass(frozen=True)
class JSONAPIObjectSchemas:
    attributes_schema: type[BaseModel]
    relationships_schema: type[BaseModel]
    object_jsonapi_schema: type[JSONAPIObjectSchema]
    can_be_included_schemas: dict[str, type[JSONAPIObjectSchema]]

    @property
    def included_schemas_list(self) -> list[type[JSONAPIObjectSchema]]:
        return list(self.can_be_included_schemas.values())


@dataclass(frozen=True)
class BuiltSchemasDTO:
    schema_in_post: type[BaseJSONAPIDataInSchema]
    schema_in_post_data: type[BaseJSONAPIItemInSchema]
    schema_in_patch: type[BaseJSONAPIDataInSchema]
    schema_in_patch_data: type[BaseJSONAPIItemInSchema]
    detail_response_schema: type[JSONAPIResultDetailSchema]
    list_response_schema: type[JSONAPIResultListSchema]


FieldValidators = dict[str, Callable]


@dataclass(frozen=True, slots=True)
class IncludedSchemaDTO:
    # (name, related_schema, relationship_info.resource_type)
    name: str
    related_schema: type[BaseModel]
    related_resource_type: str


@dataclass(frozen=False, slots=True)
class ResourceIdFieldDTO:
    field_type: type
    client_can_set_id: bool = False
    validators: dict[str, classmethod[Any, Any, Any]] = dataclass_field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SchemasInfoDTO:
    # id field
    resource_id_field: ResourceIdFieldDTO
    # pre-built attributes
    attributes_schema: type[BaseModel]
    # relationships
    relationships_schema: type[BaseModel]
    # has any required relationship
    has_required_relationship: bool
    # anything that can be included
    included_schemas: list[IncludedSchemaDTO]


class SchemaBuilder:
    # IDK if there's a better way than global caches
    # shared between ALL RoutersJSONAPI instances
    object_schemas_cache: ClassVar = {}
    relationship_schema_cache: ClassVar = {}
    base_jsonapi_object_schemas_cache: ClassVar = {}

    def __init__(
        self,
        resource_type: str,
    ):
        self._resource_type = resource_type

    def _create_schemas_objects_list(self, schema: type[BaseModel]) -> type[JSONAPIResultListSchema]:
        object_jsonapi_list_schema, list_jsonapi_schema = self.build_list_schemas(schema)
        return list_jsonapi_schema

    def _create_schemas_object_detail(self, schema: type[BaseModel]) -> type[JSONAPIResultDetailSchema]:
        object_jsonapi_detail_schema, detail_jsonapi_schema = self.build_detail_schemas(schema)
        return detail_jsonapi_schema

    def create_schemas(
        self,
        schema: type[BaseModel],
        schema_in_post: type[BaseModel] | None = None,
        schema_in_patch: type[BaseModel] | None = None,
    ) -> BuiltSchemasDTO:
        # TODO: generic?
        schema_in_post = schema_in_post or schema
        schema_name_in_post_suffix = ""

        if any(schema_in_post is cmp_schema for cmp_schema in [schema, schema_in_patch]):
            schema_name_in_post_suffix = "InPost"

        schema_in_patch = schema_in_patch or schema
        schema_name_in_patch_suffix = ""

        if any(schema_in_patch is cmp_schema for cmp_schema in [schema, schema_in_post]):
            schema_name_in_patch_suffix = "InPatch"

        schema_in_post, schema_in_post_data = self.build_schema_in(
            schema_in=schema_in_post,
            schema_name_suffix=schema_name_in_post_suffix,
            non_optional_relationships=True,
        )

        schema_in_patch, schema_in_patch_data = self.build_schema_in(
            schema_in=schema_in_patch,
            schema_name_suffix=schema_name_in_patch_suffix,
            id_field_required=True,
        )

        return BuiltSchemasDTO(
            schema_in_post=schema_in_post,
            schema_in_post_data=schema_in_post_data,
            schema_in_patch=schema_in_patch,
            schema_in_patch_data=schema_in_patch_data,
            list_response_schema=self._create_schemas_objects_list(schema),
            detail_response_schema=self._create_schemas_object_detail(schema),
        )

    def build_schema_in(
        self,
        schema_in: type[BaseModel],
        schema_name_suffix: str = "",
        *,
        non_optional_relationships: bool = False,
        id_field_required: bool = False,
    ) -> tuple[type[BaseJSONAPIDataInSchema], type[BaseJSONAPIItemInSchema]]:
        base_schema_name = schema_in.__name__.removesuffix("Schema") + schema_name_suffix

        dto = self._get_info_from_schema_for_building(
            base_name=base_schema_name,
            schema=schema_in,
            non_optional_relationships=non_optional_relationships,
        )

        object_jsonapi_schema = self._build_jsonapi_object(
            base_name=base_schema_name,
            resource_type=self._resource_type,
            schemas_info_dto=dto,
            includes=not_passed,
            model_base=BaseJSONAPIItemInSchema,
            relationships_required=dto.has_required_relationship,
            id_field_required=id_field_required,
        )

        wrapped_object_jsonapi_schema = pydantic.create_model(
            f"{base_schema_name}ObjectDataJSONAPI",
            data=(object_jsonapi_schema, ...),
            __base__=BaseJSONAPIDataInSchema,
        )

        return wrapped_object_jsonapi_schema, object_jsonapi_schema

    def _build_schema(
        self,
        base_name: str,
        schema: type[BaseModel],
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
        schema: type[BaseModel],
        includes: Iterable[str] = not_passed,
    ) -> tuple[type[JSONAPIObjectSchema], type[JSONAPIResultDetailSchema]]:
        return self._build_schema(
            base_name=f"{schema.__name__}Detail",
            schema=schema,
            builder=self.build_schema_for_detail_result,
            includes=includes,
        )

    def build_list_schemas(
        self,
        schema: type[BaseModel],
        includes: Iterable[str] = not_passed,
    ) -> tuple[type[JSONAPIObjectSchema], type[JSONAPIResultListSchema]]:
        return self._build_schema(
            base_name=f"{schema.__name__}List",
            schema=schema,
            builder=self.build_schema_for_list_result,
            includes=includes,
        )

    @classmethod
    def _annotation_with_validators(cls, field: FieldInfo) -> type:
        annotation = field.annotation
        validators = []
        for val in field.metadata:
            if isinstance(val, BeforeValidator | AfterValidator):
                validators.append(val)

        if validators:
            annotation = Annotated[annotation, *validators]

        return annotation

    def _get_info_from_schema_for_building(
        self,
        base_name: str,
        schema: type[BaseModel],
        includes: Iterable[str] = not_passed,
        *,
        non_optional_relationships: bool = False,
    ) -> SchemasInfoDTO:
        attributes_schema_fields = {}
        relationships_schema_fields = {}
        included_schemas: list[IncludedSchemaDTO] = []
        has_required_relationship = False
        resource_id_field = ResourceIdFieldDTO(field_type=str)

        # required! otherwise we get ForwardRef
        schema.model_rebuild(_types_namespace=registry.schemas)
        # TODO: can schema.model_fields be empty?
        # annotation for schema to have `model_fields`
        for name, field in (schema.model_fields or {}).items():
            if relationship_info := get_relationship_info_from_field_metadata(field):
                if includes is not_passed:
                    pass
                elif name not in includes:
                    # if includes are passed, skip this if name not present!
                    continue
                relationship_schema = self.create_relationship_data_schema(
                    field_name=name,
                    base_name=base_name,
                    field=field,
                    relationship_info=relationship_info,
                )
                field_marked_required = field.is_required()
                relationship_field = ... if (non_optional_relationships and field_marked_required) else None
                if relationship_field is not None:
                    has_required_relationship = True
                relationships_schema_fields[name] = (relationship_schema, relationship_field)
                # works both for to-one and to-many
                related_schema = get_schema_from_field_annotation(field)
                if related_schema:
                    included_schemas.append(
                        IncludedSchemaDTO(
                            name=name,
                            related_schema=related_schema,
                            related_resource_type=relationship_info.resource_type,
                        ),
                    )
                else:
                    log.warning("Could not find related schema in field %s", field)
            elif name == "id":
                id_validators = extract_field_validators(
                    model=schema,
                    include_for_field_names={"id"},
                )
                resource_id_field.validators = id_validators

                if not (can_set_id := search_client_can_set_id.first(field)):
                    continue

                resource_id_field.field_type = self._annotation_with_validators(field=field)
                resource_id_field.client_can_set_id = can_set_id
            else:
                annotation = self._annotation_with_validators(field=field)
                attributes_schema_fields[name] = (annotation, field.default)

        model_config = ConfigDict(from_attributes=True)

        extracted_validators = extract_field_validators(schema, exclude_for_field_names={"id"})
        attributes_schema = pydantic.create_model(
            f"{base_name}AttributesJSONAPI",
            **attributes_schema_fields,
            __config__=model_config,
            __validators__=extracted_validators,
        )

        relationships_schema = pydantic.create_model(
            f"{base_name}RelationshipsJSONAPI",
            **relationships_schema_fields,
            __config__=model_config,
        )

        return SchemasInfoDTO(
            resource_id_field=resource_id_field,
            attributes_schema=attributes_schema,
            relationships_schema=relationships_schema,
            has_required_relationship=has_required_relationship,
            included_schemas=included_schemas,
        )

    @classmethod
    def create_relationship_schema(
        cls,
        name: str,
        relationship_info: RelationshipInfo,
    ) -> type[BaseJSONAPIRelationshipSchema]:
        # TODO: cache?
        if name.endswith("s"):
            # plural to single
            name = name[:-1]

        schema_name = f"{name}RelationshipJSONAPI".format(name=name)
        return pydantic.create_model(
            schema_name,
            id=(str, Field(..., description="Resource object id", example=relationship_info.resource_id_example)),
            type=(str, Field(default=relationship_info.resource_type, description="Resource type")),
            __base__=BaseJSONAPIRelationshipSchema,
        )

    def create_relationship_data_schema(
        self,
        field_name: str,
        base_name: str,
        field: FieldInfo,
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
            relationship_schema = list[relationship_schema]
            base = BaseJSONAPIRelationshipDataToManySchema
        elif not field.is_required():
            relationship_schema = relationship_schema | None

        relationship_data_schema = pydantic.create_model(
            f"{schema_name}RelationshipDataJSONAPI",
            # TODO: on create (post request) sometimes it's required and at the same time on fetch it's not required
            data=(relationship_schema, Field(... if field.is_required() else None)),
            __base__=base,
        )
        self.relationship_schema_cache[cache_key] = relationship_data_schema
        return relationship_data_schema

    @classmethod
    def _build_relationships_schema_definition(
        cls,
        relationships_required: bool,
        relationships_schema: type[BaseModel],
    ) -> tuple:
        default = ...
        if not relationships_required:
            default = None
            relationships_schema = relationships_schema | None
        field_definition = (relationships_schema | None, default)
        return field_definition

    @classmethod
    def _build_object_jsonapi_schema_fields(
        cls,
        attributes_schema,
        resource_id_field: ResourceIdFieldDTO,
        id_field_required: bool,
        resource_type: str,
    ) -> dict:
        id_type = resource_id_field.field_type

        if resource_id_field.client_can_set_id:
            id_type = Annotated[id_type, resource_id_field.client_can_set_id]

        object_jsonapi_schema_fields = {}
        object_jsonapi_schema_fields.update(
            id=(id_type, Field(... if id_field_required else None)),
            attributes=(attributes_schema, ...),
            type=(str, Field(default=resource_type, description="Resource type")),
        )
        return object_jsonapi_schema_fields

    def _build_jsonapi_object(
        self,
        base_name: str,
        resource_type: str,
        schemas_info_dto: SchemasInfoDTO,
        includes,
        model_base: type[JSONAPIObjectSchemaType] = JSONAPIObjectSchema,
        *,
        use_schema_cache: bool = True,
        relationships_required: bool = False,
        id_field_required: bool = False,
    ) -> type[JSONAPIObjectSchemaType]:
        if use_schema_cache and base_name in self.base_jsonapi_object_schemas_cache:
            return self.base_jsonapi_object_schemas_cache[base_name]

        # todo: pass all decorator infos for whole schema for attributes schema
        object_jsonapi_schema_fields = self._build_object_jsonapi_schema_fields(
            attributes_schema=schemas_info_dto.attributes_schema,
            resource_id_field=schemas_info_dto.resource_id_field,
            id_field_required=id_field_required,
            resource_type=resource_type or self._resource_type,
        )
        if includes:
            object_jsonapi_schema_fields.update(
                relationships=self._build_relationships_schema_definition(
                    relationships_required=relationships_required,
                    relationships_schema=schemas_info_dto.relationships_schema,
                ),
            )

        object_jsonapi_schema = pydantic.create_model(
            f"{base_name}ObjectJSONAPI",
            **object_jsonapi_schema_fields,
            __validators__=schemas_info_dto.resource_id_field.validators,
            __base__=model_base,
        )

        if use_schema_cache:
            self.base_jsonapi_object_schemas_cache[base_name] = object_jsonapi_schema

        return object_jsonapi_schema

    def find_all_included_schemas(
        self,
        schema: type[BaseModel],
        resource_type: str,
        includes: Iterable[str],
        included_schemas: list[IncludedSchemaDTO],
    ) -> dict[str, type[JSONAPIObjectSchema]]:
        if includes is not_passed:
            return {
                # prepare same object schema
                # TODO: caches?!
                i.name: self.create_jsonapi_object_schemas(
                    i.related_schema,
                    resource_type=i.related_resource_type,
                ).object_jsonapi_schema
                for i in included_schemas
            }

        return self.find_all_included_schemas_from_annotations(
            schema=schema,
            resource_type=resource_type,
            includes=includes,
        )

    def find_all_included_schemas_from_annotations(
        self,
        schema: type[BaseModel],
        resource_type: str,
        includes: Iterable[str],
    ) -> dict[str, type[JSONAPIObjectSchema]]:
        can_be_included_schemas: dict[str, type[JSONAPIObjectSchema]] = {}
        for i_include in includes:
            current_schema = schema
            relations_list: list[str] = i_include.split(SPLIT_REL)
            for part_index, include_part in enumerate(relations_list, start=1):
                # find nested from the Schema
                nested_schema = get_schema_from_field_annotation(current_schema.model_fields[include_part])
                # TODO: ? continue or raise? probably should be already checked
                assert nested_schema is not None
                # find all relations for this one
                nested_schema_includes = set(relations_list[: part_index - 1] + relations_list[part_index:])
                related_jsonapi_object_schema = self.create_jsonapi_object_schemas(
                    nested_schema,
                    resource_type=resource_type,
                    # higher and lower
                    includes=nested_schema_includes,
                    # rebuild schemas for each response
                    use_schema_cache=False,
                ).object_jsonapi_schema
                # cache it
                can_be_included_schemas[include_part] = related_jsonapi_object_schema
                # prepare for the next step
                current_schema = nested_schema

        return can_be_included_schemas

    def create_jsonapi_object_schemas(
        self,
        schema: type[BaseModel],
        includes: Iterable[str] = not_passed,
        resource_type: str | None = None,
        base_name: str = "",
        *,
        compute_included_schemas: bool = False,
        use_schema_cache: bool = True,
    ) -> JSONAPIObjectSchemas:
        # TODO: more caching (how? for each includes...)

        if use_schema_cache and schema in self.object_schemas_cache and includes is not_passed:
            return self.object_schemas_cache[schema]

        base_name = base_name or schema.__name__

        if includes is not not_passed:
            includes = set(includes)

        dto = self._get_info_from_schema_for_building(
            base_name=base_name,
            schema=schema,
            includes=includes,
        )

        object_jsonapi_schema = self._build_jsonapi_object(
            base_name=base_name,
            resource_type=resource_type,
            schemas_info_dto=dto,
            includes=includes,
            use_schema_cache=use_schema_cache,
            # pass has_required_relationship ?
            relationships_required=False,
        )

        can_be_included_schemas = {}
        if compute_included_schemas:
            can_be_included_schemas = self.find_all_included_schemas(
                schema=schema,
                resource_type=resource_type,
                includes=includes,
                included_schemas=dto.included_schemas,
            )

        result = JSONAPIObjectSchemas(
            attributes_schema=dto.attributes_schema,
            relationships_schema=dto.relationships_schema,
            object_jsonapi_schema=object_jsonapi_schema,
            can_be_included_schemas=can_be_included_schemas,
        )
        if use_schema_cache and includes is not_passed:
            self.object_schemas_cache[schema] = result
        return result

    def build_schema_for_list_result(
        self,
        name: str,
        object_jsonapi_schema: type[JSONAPIObjectSchema],
        includes_schemas: list[type[JSONAPIObjectSchema]],
    ) -> type[JSONAPIResultListSchema]:
        return self.build_schema_for_result(
            name=f"{name}JSONAPI",
            base=JSONAPIResultListSchema,
            data_type=list[object_jsonapi_schema],
            includes_schemas=includes_schemas,
        )

    def build_schema_for_detail_result(
        self,
        name: str,
        object_jsonapi_schema: type[JSONAPIObjectSchema],
        includes_schemas: list[type[JSONAPIObjectSchema]],
    ) -> type[JSONAPIResultDetailSchema]:
        return self.build_schema_for_result(
            name=f"{name}JSONAPI",
            base=JSONAPIResultDetailSchema,
            data_type=object_jsonapi_schema,
            includes_schemas=includes_schemas,
        )

    def build_schema_for_result(
        self,
        name: str,
        base: type[BaseJSONAPIResultSchema],
        data_type: type[JSONAPIObjectSchema | list[JSONAPIObjectSchema]],
        includes_schemas: list[type[JSONAPIObjectSchema]],
    ) -> type[JSONAPIResultListSchema | JSONAPIResultDetailSchema]:
        included_schema_annotation = Union[JSONAPIObjectSchema]
        for includes_schema in includes_schemas:
            included_schema_annotation = Union[included_schema_annotation, includes_schema]

        schema_fields = {}
        schema_fields.update(
            data=(data_type, ...),
        )
        if includes_schemas:
            schema_fields.update(
                included=(
                    list[included_schema_annotation],
                    Field(None),
                ),
            )

        return pydantic.create_model(
            name,
            **schema_fields,
            __base__=base,
        )
