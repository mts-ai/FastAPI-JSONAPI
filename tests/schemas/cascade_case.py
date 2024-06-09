from __future__ import annotations

from typing import Annotated

from fastapi_jsonapi.schema_base import (
    BaseModel,
)
from fastapi_jsonapi.types_metadata import RelationshipInfo


class CascadeCaseSchema(BaseModel):
    parent_item: Annotated[
        CascadeCaseSchema | None,
        RelationshipInfo(
            resource_type="cascade_case",
        ),
    ] = None
    sub_items: Annotated[
        list[CascadeCaseSchema] | None,
        RelationshipInfo(
            resource_type="cascade_case",
            many=True,
        ),
    ] = None
