from __future__ import annotations

from typing import (
    Annotated,
    TYPE_CHECKING,
)

from pydantic import ConfigDict
from fastapi_jsonapi.schema_base import (
    BaseModel,
)
from fastapi_jsonapi.types_metadata import RelationshipInfo

if TYPE_CHECKING:
    from tests.schemas.parent_to_child import ParentToChildAssociationSchema


class ChildAttributesSchema(BaseModel):
    name: str
    model_config = ConfigDict(from_attributes=True)


class ChildBaseSchema(ChildAttributesSchema):
    """Child base schema."""

    parents: Annotated[
        list[ParentToChildAssociationSchema] | None,
        RelationshipInfo(
            resource_type="parent_child_association",
            many=True,
        ),
    ] = None


class ChildPatchSchema(ChildBaseSchema):
    """Child PATCH schema."""


class ChildInSchema(ChildBaseSchema):
    """Child input schema."""


class ChildSchema(ChildInSchema):
    """Child item schema."""

    id: int
