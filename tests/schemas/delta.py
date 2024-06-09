from __future__ import annotations

from typing import Annotated, TYPE_CHECKING
from fastapi_jsonapi.schema_base import (
    BaseModel,
)
from fastapi_jsonapi.types_metadata import RelationshipInfo

if TYPE_CHECKING:
    from tests.schemas.beta import BetaSchema
    from tests.schemas.gamma import GammaSchema


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
