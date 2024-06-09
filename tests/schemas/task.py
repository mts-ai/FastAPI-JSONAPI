from __future__ import annotations

from typing import Optional
from pydantic import (
    ConfigDict,
    field_validator,
)

from fastapi_jsonapi.schema_base import BaseModel


class TaskBaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    # TODO: check BeforeValidator annotated
    task_ids: list[str] | None = None

    # noinspection PyMethodParameters
    @field_validator("task_ids", mode="before", check_fields=False)
    @classmethod
    def task_ids_validator(cls, value: list[str] | None):
        """
        return `[]`, if value is None both on get and on create
        """
        return value or []


class TaskPatchSchema(TaskBaseSchema):
    """Task PATCH schema."""


class TaskInSchema(TaskBaseSchema):
    """Task create schema."""


class TaskSchema(TaskBaseSchema):
    """Task item schema."""

    id: int
