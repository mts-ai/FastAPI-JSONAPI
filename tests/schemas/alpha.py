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
    from tests.schemas.gamma import GammaSchema
    from tests.schemas.beta import BetaSchema


class AlphaSchema(BaseModel):
    beta: Annotated[
        BetaSchema | None,
        RelationshipInfo(
            resource_type="beta",
        ),
    ] = None
    gamma: Annotated[
        GammaSchema | None,
        RelationshipInfo(
            resource_type="gamma",
        ),
    ] = None
