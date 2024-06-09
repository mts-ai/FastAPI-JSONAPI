"""JSON API schemas builder class."""

import logging
from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    Annotated,
)

import pydantic
from fastapi_jsonapi.common import (
    search_client_can_set_id,
    get_relationship_info_from_field_metadata,
)
from fastapi_jsonapi.types_metadata import ClientCanSetId
from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict
from pydantic.fields import FieldInfo

from fastapi_jsonapi.data_typing import TypeSchema
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
from fastapi_jsonapi.types_metadata import RelationshipInfo
from fastapi_jsonapi.splitter import SPLIT_REL
from fastapi_jsonapi.validation_utils import (
    extract_field_validators,
    extract_validators,
)

JSON_API_RESPONSE_TYPE = Dict[Union[int, str], Dict[str, Any]]

JSONAPIObjectSchemaType = TypeVar("JSONAPIObjectSchemaType", bound=PydanticBaseModel)

not_passed = object()

log = logging.getLogger(__name__)


# TODO: check in runtime and update dataclass kwargs
# todo: when 3.9 support is dropped, return back `slots=True to JSONAPIObjectSchemas dataclass`


class FieldConfig:
    cast_type: Callable

    def __init__(self, cast_type: Optional[Callable] = None):
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
    schema_in_post_data: Type[BaseJSONAPIItemInSchema]
    schema_in_patch: Type[BaseJSONAPIDataInSchema]
    schema_in_patch_data: Type[BaseJSONAPIItemInSchema]
    detail_response_schema: Type[JSONAPIResultDetailSchema]
    list_response_schema: Type[JSONAPIResultListSchema]


FieldValidators = Dict[str, Callable]


@dataclass(frozen=True)
class SchemasInfoDTO:
    # id field
    resource_id_field: tuple[Type, FieldInfo, Callable, FieldValidators]
    # pre-built attributes
    attributes_schema: Type[BaseModel]
    # relationships
    relationships_schema: Type[BaseModel]
    # has any required relationship
    has_required_relationship: bool
    # anything that can be included
    included_schemas: list[tuple[str, BaseModel, str]]


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

    def _create_schemas_objects_list(self, schema: Type[BaseModel]) -> Type[JSONAPIResultListSchema]:
        object_jsonapi_list_schema, list_jsonapi_schema = self.build_list_schemas(schema)
        return list_jsonapi_schema

    def _create_schemas_object_detail(self, schema: Type[BaseModel]) -> Type[JSONAPIResultDetailSchema]:
        object_jsonapi_detail_schema, detail_jsonapi_schema = self.build_detail_schemas(schema)
        return detail_jsonapi_schema

    def create_schemas(
        self,
        schema: Type[BaseModel],
        schema_in_post: Optional[Type[BaseModel]] = None,
        schema_in_patch: Optional[Type[BaseModel]] = None,
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
        schema_in: Type[BaseModel],
        schema_name_suffix: str = "",
        non_optional_relationships: bool = False,
        id_field_required: bool = False,
    ) -> Tuple[Type[BaseJSONAPIDataInSchema], Type[BaseJSONAPIItemInSchema]]:
        base_schema_name = schema_in.__name__.removesuffix("Schema") + schema_name_suffix

        dto = self._get_info_from_schema_for_building(
            base_name=base_schema_name,
            schema=schema_in,
            non_optional_relationships=non_optional_relationships,
        )

        object_jsonapi_schema = self._build_jsonapi_object(
            base_name=base_schema_name,
            resource_type=self._resource_type,
            attributes_schema=dto.attributes_schema,
            relationships_schema=dto.relationships_schema,
            resource_id_field=dto.resource_id_field,
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
        non_optional_relationships: bool = False,
    ) -> SchemasInfoDTO:
        attributes_schema_fields = {}
        relationships_schema_fields = {}
        # TODO: dto? instead of tuples
        included_schemas: list[tuple[str, Optional[type], str]] = []
        has_required_relationship = False
        resource_id_field = (str, Field(None), None, {})

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
                # consider field is not required until is marked required explicitly (`default=...` means required)
                field_marked_required = field.is_required() is True
                relationship_field = ... if (non_optional_relationships and field_marked_required) else None
                if relationship_field is not None:
                    has_required_relationship = True
                relationships_schema_fields[name] = (relationship_schema, relationship_field)
                # works both for to-one and to-many
                related_schema = get_schema_from_field_annotation(field)
                if related_schema:
                    included_schemas.append((name, related_schema, relationship_info.resource_type))
                else:
                    log.warning("Could not find related schema in field %s", field)
            elif name == "id":
                id_validators = extract_field_validators(
                    model=schema,
                    include_for_field_names={"id"},
                )
                resource_id_field = (*(resource_id_field[:-1]), id_validators)

                if not search_client_can_set_id.first(field):
                    continue

                # todo: support for union types?
                #  support custom cast func.. already?
                resource_id_field = (
                    # id always is string!
                    str,
                    # get the same default
                    Field(default=field.default),
                    # annotation
                    field.annotation,
                    # and validators
                    id_validators,
                )
            else:
                attributes_schema_fields[name] = (field.annotation, field.default)
        model_config = ConfigDict(from_attributes=True)

        extracted_validators = extract_validators(schema, exclude_for_field_names={"id"})
        model_create = dict(
            **attributes_schema_fields,
            __config__=model_config,
            __validators__=extracted_validators,
        )
        attributes_schema = pydantic.create_model(
            f"{base_name}AttributesJSONAPI",
            **model_create,
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
            # TODO: rework type annotation?
            included_schemas=included_schemas,
        )

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
            relationship_schema = Optional[relationship_schema]

        relationship_data_schema = pydantic.create_model(
            f"{schema_name}RelationshipDataJSONAPI",
            # TODO: on create (post request) sometimes it's required and at the same time on fetch it's not required
            data=(relationship_schema, Field(... if field.is_required() else None)),
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
        resource_id_field: Tuple[Type, FieldInfo, Callable, FieldValidators],
        model_base: Type[JSONAPIObjectSchemaType] = JSONAPIObjectSchema,
        use_schema_cache: bool = True,
        relationships_required: bool = False,
        id_field_required: bool = False,
    ) -> Type[JSONAPIObjectSchemaType]:
        if use_schema_cache and base_name in self.base_jsonapi_object_schemas_cache:
            return self.base_jsonapi_object_schemas_cache[base_name]

        field_type, field_info, id_cast_func, id_validators = resource_id_field

        id_type = str

        if id_cast_func:
            id_type = Annotated[str, ClientCanSetId(cast_type=id_cast_func)]

        object_jsonapi_schema_fields = {
            "attributes": (attributes_schema, ...),
            "id": (id_type, Field(... if id_field_required else None)),
        }
        if includes:
            object_jsonapi_schema_fields.update(
                relationships=(Optional[relationships_schema], (... if relationships_required else None)),
            )

        default_resource_type = resource_type or self._resource_type
        # ?? types?
        object_jsonapi_schema = pydantic.create_model(
            f"{base_name}ObjectJSONAPI",
            **object_jsonapi_schema_fields,
            type=(str, Field(default=default_resource_type, description="Resource type")),
            __validators__=id_validators,
            __base__=model_base,
        )

        if use_schema_cache:
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
                nested_schema = get_schema_from_field_annotation(current_schema.model_fields[include_part])
                # TODO? continue or raise?
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
        schema: Type[BaseModel],
        includes: Iterable[str] = not_passed,
        resource_type: Optional[str] = None,
        base_name: str = "",
        compute_included_schemas: bool = False,
        use_schema_cache: bool = True,
    ) -> JSONAPIObjectSchemas:
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
            attributes_schema=dto.attributes_schema,
            relationships_schema=dto.relationships_schema,
            resource_id_field=dto.resource_id_field,
            includes=includes,
            use_schema_cache=use_schema_cache,
            # pass has_required_relationship ?
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
