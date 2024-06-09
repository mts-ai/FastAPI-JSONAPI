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
    from tests.schemas.user import UserSchema


class ComputerAttributesBaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str


class ComputerBaseSchema(ComputerAttributesBaseSchema):
    """Computer base schema."""

    user: Annotated[
        UserSchema | None,
        RelationshipInfo(
            resource_type="user",
        ),
    ] = None


class ComputerPatchSchema(ComputerBaseSchema):
    """Computer PATCH schema."""


class ComputerInSchema(ComputerBaseSchema):
    """Computer input schema."""


class ComputerSchema(ComputerInSchema):
    """Computer item schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int

    # TODO: rename
    # owner: UserSchema | None"] = Field(
    user: Annotated[
        UserSchema | None,
        RelationshipInfo(
            resource_type="user",
        ),
    ] = None
