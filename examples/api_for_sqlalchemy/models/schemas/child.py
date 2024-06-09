from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Annotated,
)

from pydantic import ConfigDict

from fastapi_jsonapi.schema_base import (
    BaseModel,
)
from fastapi_jsonapi.types_metadata import RelationshipInfo

if TYPE_CHECKING:
    from .parent_child_association import ParentToChildAssociationSchema


class ChildBaseSchema(BaseModel):
    """Child base schema."""

    model_config = ConfigDict(from_attributes=True)

    name: str

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
