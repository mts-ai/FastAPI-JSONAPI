from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi_jsonapi.schema_base import (
    BaseModel,
)
from fastapi_jsonapi.types_metadata import RelationshipInfo

if TYPE_CHECKING:
    from tests.schemas import BetaSchema, GammaSchema


class DeltaSchema(BaseModel):
    name: str
    gammas: Annotated[
        GammaSchema | None,
        RelationshipInfo(
            resource_type="gamma",
            many=True,
        ),
    ] = None
    betas: Annotated[
        BetaSchema | None,
        RelationshipInfo(
            resource_type="beta",
            many=True,
        ),
    ] = None
