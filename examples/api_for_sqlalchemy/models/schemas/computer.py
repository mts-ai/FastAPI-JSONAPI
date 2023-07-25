"""Computer schemas module."""

from typing import TYPE_CHECKING, Optional

from fastapi_jsonapi.schema_base import BaseModel, Field, RelationshipInfo

if TYPE_CHECKING:
    from .user import UserSchema


class ComputerBaseSchema(BaseModel):
    """Computer base schema."""

    class Config:
        """Pydantic schema config."""

        orm_mode = True

    name: str
    user: Optional["UserSchema"] = Field(
        relationship=RelationshipInfo(
            resource_type="user",
        ),
    )


class ComputerPatchSchema(ComputerBaseSchema):
    """Computer PATCH schema."""


class ComputerInSchema(ComputerBaseSchema):
    """Computer input schema."""


class ComputerSchema(ComputerInSchema):
    """Computer item schema."""

    class Config:
        """Pydantic model config."""

        orm_mode = True

    id: int
