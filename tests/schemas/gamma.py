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
    from tests.schemas.beta import BetaSchema
    from tests.schemas.delta import DeltaSchema


class GammaSchema(BaseModel):
    betas: Annotated[
        BetaSchema | None,
        RelationshipInfo(
            resource_type="beta",
            many=True,
        ),
    ] = None
    delta: Annotated[
        DeltaSchema | None,
        RelationshipInfo(
            resource_type="Delta",
        ),
    ] = None
