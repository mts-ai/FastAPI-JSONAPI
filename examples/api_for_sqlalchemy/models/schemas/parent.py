from typing import TYPE_CHECKING, List

from fastapi_jsonapi.schema_base import BaseModel, Field, RelationshipInfo

if TYPE_CHECKING:
    from .parent_child_association import ParentToChildAssociationSchema


class ParentBaseSchema(BaseModel):
    """Parent base schema."""

    class Config:
        """Pydantic schema config."""

        orm_mode = True

    name: str


class ParentPatchSchema(ParentBaseSchema):
    """Parent PATCH schema."""


class ParentInSchema(ParentBaseSchema):
    """Parent input schema."""


class ParentSchema(ParentInSchema):
    """PostComment item schema."""

    class Config:
        """Pydantic model config."""

        orm_mode = True

    id: int

    children: List["ParentToChildAssociationSchema"] = Field(
        relationship=RelationshipInfo(
            resource_type="parent_child_association",
            many=True,
        ),
    )
