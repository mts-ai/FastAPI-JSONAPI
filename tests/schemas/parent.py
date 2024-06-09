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
    from tests.schemas import ParentToChildAssociationSchema


class ParentAttributesSchema(BaseModel):
    name: str
    model_config = ConfigDict(from_attributes=True)


class ParentBaseSchema(ParentAttributesSchema):
    """Parent base schema."""

    children: Annotated[
        ParentToChildAssociationSchema | None,
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
