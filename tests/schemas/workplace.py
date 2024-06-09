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
    from tests.schemas import UserSchema


class WorkplaceBaseSchema(BaseModel):
    """Workplace base schema."""

    model_config = ConfigDict(from_attributes=True)

    name: str
    user: Annotated[
        UserSchema | None,
        RelationshipInfo(
            resource_type="user",
        ),
    ] = None


class WorkplacePatchSchema(WorkplaceBaseSchema):
    """Workplace PATCH schema."""


class WorkplaceInSchema(WorkplaceBaseSchema):
    """Workplace input schema."""


class WorkplaceSchema(WorkplaceInSchema):
    """Workplace item schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
