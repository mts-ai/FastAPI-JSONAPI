from __future__ import annotations

from typing import (
    Annotated,
    TYPE_CHECKING,
)
from fastapi_jsonapi.schema_base import (
    BaseModel,
)
from fastapi_jsonapi.types_metadata import RelationshipInfo

if TYPE_CHECKING:
    from tests.schemas import AlphaSchema, DeltaSchema, GammaSchema


class BetaSchema(BaseModel):
    alphas: Annotated[
        AlphaSchema | None,
        RelationshipInfo(
            resource_type="alpha",
        ),
    ] = None
    gammas: Annotated[
        GammaSchema | None,
        RelationshipInfo(
            resource_type="gamma",
            many=True,
        ),
    ] = None
    deltas: Annotated[
        DeltaSchema | None,
        RelationshipInfo(
            resource_type="delta",
            many=True,
        ),
    ] = None
