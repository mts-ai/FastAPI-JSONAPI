"""Computer schemas module."""

from typing import TYPE_CHECKING, Optional

from pydantic import ConfigDict

from fastapi_jsonapi.schema_base import BaseModel, Field, RelationshipInfo

if TYPE_CHECKING:
    from .user import UserSchema


class ComputerBaseSchema(BaseModel):
    """Computer base schema."""

    model_config = ConfigDict(from_attributes=True)

    name: str
    user: Optional["UserSchema"] = Field(
        json_schema_extra={
            "relationship": RelationshipInfo(
                resource_type="user",
            ),
        },
    )


class ComputerPatchSchema(ComputerBaseSchema):
    """Computer PATCH schema."""


class ComputerInSchema(ComputerBaseSchema):
    """Computer input schema."""


class ComputerSchema(ComputerInSchema):
    """Computer item schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
