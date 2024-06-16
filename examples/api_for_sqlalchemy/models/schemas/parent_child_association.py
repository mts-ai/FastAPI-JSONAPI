from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Annotated,
)

from fastapi_jsonapi.schema_base import (
    BaseModel,
)
from fastapi_jsonapi.types_metadata import RelationshipInfo

if TYPE_CHECKING:
    from .child import ChildSchema
    from .parent import ParentSchema


class ParentToChildAssociationSchema(BaseModel):
    id: int
    extra_data: str

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
