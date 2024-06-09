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


class ParentBaseSchema(BaseModel):
    """Parent base schema."""

    model_config = ConfigDict(from_attributes=True)

    name: str

    children: Annotated[
        list[ParentToChildAssociationSchema] | None,
        RelationshipInfo(
            resource_type="parent_child_association",
            many=True,
        ),
    ] = None


class ParentPatchSchema(ParentBaseSchema):
    """Parent PATCH schema."""


class ParentInSchema(ParentBaseSchema):
    """Parent input schema."""


class ParentSchema(ParentInSchema):
    """Parent item schema."""

    id: int
