from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
from typing import Any

from fastapi_jsonapi.schema import (
    BaseJSONAPIDataInSchema,
    BaseJSONAPIItemInSchema,
    JSONAPIResultDetailSchema,
    JSONAPIResultListSchema,
)
from fastapi_jsonapi.schema_base import BaseModel


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


@dataclass(frozen=True)
class BuiltSchemasDTO:
    schema_in_post: type[BaseJSONAPIDataInSchema]
    schema_in_post_data: type[BaseJSONAPIItemInSchema]
    schema_in_patch: type[BaseJSONAPIDataInSchema]
    schema_in_patch_data: type[BaseJSONAPIItemInSchema]
    detail_response_schema: type[JSONAPIResultDetailSchema]
    list_response_schema: type[JSONAPIResultListSchema]
