from __future__ import annotations

from typing import Annotated

from fastapi_jsonapi.schema_base import (
    BaseModel,
)
from fastapi_jsonapi.types_metadata import RelationshipInfo


class SelfRelationshipAttributesSchema(BaseModel):
    name: str
    parent_object: Annotated[
        SelfRelationshipAttributesSchema | None,
        RelationshipInfo(
            resource_type="self_relationship",
        ),
    ] = None
    children_objects: Annotated[
        list[SelfRelationshipAttributesSchema] | None,
        RelationshipInfo(
            resource_type="self_relationship",
            many=True,
        ),
    ] = None
