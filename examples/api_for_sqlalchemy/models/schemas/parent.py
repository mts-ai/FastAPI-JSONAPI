from typing import TYPE_CHECKING, List

from fastapi_jsonapi.schema_base import BaseModel, Field, RelationshipInfo

if TYPE_CHECKING:
    from .parent_child_association import ParentToChildAssociationSchema


class ParentBaseSchema(BaseModel):
    """Parent base schema."""

    class Config:
        orm_mode = True

    name: str

    children: List["ParentToChildAssociationSchema"] = Field(
        default=None,
        relationship=RelationshipInfo(
            resource_type="parent_child_association",
            many=True,
        ),
    )


class ParentPatchSchema(ParentBaseSchema):
    """Parent PATCH schema."""


class ParentInSchema(ParentBaseSchema):
    """Parent input schema."""


class ParentSchema(ParentInSchema):
    """Parent item schema."""

    id: int
