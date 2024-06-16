"""Collection of useful http error for the Api."""
from __future__ import annotations

from typing import (
    Any,
)

from pydantic import Field
from pydantic.main import BaseModel


class ExceptionSourceSchema(BaseModel):
    """Source exception schema."""

    parameter: str | None = None
    pointer: str | None = None


class ExceptionSchema(BaseModel):
    """Exception schema."""

    status: str
    source: ExceptionSourceSchema | None = None
    title: str
    detail: Any = None


class ExceptionResponseSchema(BaseModel):
    """Exception response schema."""

    errors: list[ExceptionSchema]
    jsonapi: dict[str, str] = Field(default={"version": "1.0"})


class QueryError(Exception):
    """Query build error."""
