"""Collection of useful http error for the Api."""

from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from pydantic import Field
from pydantic.main import BaseModel


class ExceptionSourceSchema(BaseModel):
    """Source exception schema."""

    parameter: Optional[str] = None
    pointer: Optional[str] = None


class ExceptionSchema(BaseModel):
    """Exception schema."""

    status: str
    source: Optional[ExceptionSourceSchema] = None
    title: str
    detail: Any


class ExceptionResponseSchema(BaseModel):
    """Exception response schema."""

    errors: List[ExceptionSchema]
    jsonapi: Dict[str, str] = Field(default={"version": "1.0"})


class QueryError(Exception):
    """Query build error."""
