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
    from tests.schemas import ChildSchema, ParentSchema


class ParentToChildAssociationAttributesSchema(BaseModel):
    extra_data: str
    model_config = ConfigDict(from_attributes=True)


class ParentToChildAssociationSchema(ParentToChildAssociationAttributesSchema):
    parent: Annotated[
        ParentSchema | None,
        RelationshipInfo(
            resource_type="parent",
        ),
    ] = None

    child: Annotated[
        ChildSchema | None,
        RelationshipInfo(
            resource_type="child",
        ),
    ] = None
