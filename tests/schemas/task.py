from __future__ import annotations

from typing import Annotated

from pydantic import (
    ConfigDict,
    field_validator,
    BeforeValidator,
)

from fastapi_jsonapi.schema_base import BaseModel


def func_validator(value: list[str] | None) -> list[str]:
    """
    return `[]`, if value is None both on get and on create

    :param value:
    :return:
    """
    return value or []


class TaskBaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    # TODO: check BeforeValidator annotated
    task_ids: list[str] | None = None
    another_task_ids: Annotated[list[str] | None, BeforeValidator(func_validator)]

    # noinspection PyMethodParameters
    @field_validator("task_ids", mode="before")
    @staticmethod
    def task_ids_validator(value: list[str] | None):
        """
        return `[]`, if value is None both on get and on create
        """
        return func_validator(value)


class TaskPatchSchema(TaskBaseSchema):
    """Task PATCH schema."""


class TaskInSchema(TaskBaseSchema):
    """Task create schema."""


class TaskSchema(TaskBaseSchema):
    """Task item schema."""

    id: int
