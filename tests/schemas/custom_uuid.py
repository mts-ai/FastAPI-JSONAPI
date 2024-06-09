from __future__ import annotations

from typing import (
    Optional,
    Annotated,
)
from uuid import UUID

from fastapi_jsonapi.types_metadata import ClientCanSetId
from pydantic import (
    ConfigDict,
    Field,
)

from fastapi_jsonapi.schema_base import BaseModel


class CustomUUIDItemAttributesSchema(BaseModel):
    extra_id: Optional[UUID] = None
    model_config = ConfigDict(from_attributes=True)


class CustomUUIDItemSchema(CustomUUIDItemAttributesSchema):
    id: Annotated[UUID, ClientCanSetId()]
