from typing import TYPE_CHECKING, List

from pydantic import ConfigDict

from fastapi_jsonapi.schema_base import BaseModel, Field, RelationshipInfo

if TYPE_CHECKING:
    from .parent_child_association import ParentToChildAssociationSchema


class ChildBaseSchema(BaseModel):
    """Child base schema."""

    model_config = ConfigDict(from_attributes=True)

    name: str

    parents: List["ParentToChildAssociationSchema"] = Field(
        default=None,
        relationship=RelationshipInfo(
            resource_type="parent_child_association",
            many=True,
        ),
    )


class ChildPatchSchema(ChildBaseSchema):
    """Child PATCH schema."""


class ChildInSchema(ChildBaseSchema):
    """Child input schema."""


class ChildSchema(ChildInSchema):
    """Child item schema."""

    id: int
