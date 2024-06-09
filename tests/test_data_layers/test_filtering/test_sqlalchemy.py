import pytest
from typing import Any
from unittest.mock import MagicMock, Mock

from fastapi import status
from pydantic import BaseModel, ConfigDict

from fastapi_jsonapi.data_layers.filtering.sqlalchemy import (
    build_filter_expression,
)
from fastapi_jsonapi.exceptions import InvalidType


class TestFilteringFuncs:
    def test_user_type_cast_success(self):
        class UserType:
            def __init__(self, *args, **kwargs):
                """This method is needed to handle incoming arguments"""

        class ModelSchema(BaseModel):
            value: UserType
            model_config = ConfigDict(arbitrary_types_allowed=True)

        model_column_mock = MagicMock()

        # field name for model ModelSchema
        field_name = "value"
        build_filter_expression(
            field_name=field_name,
            schema_field=ModelSchema.model_fields[field_name],
            model_column=model_column_mock,
            operator="__eq__",
            value=Any,
        )

        model_column_mock.__eq__.assert_called_once()

        call_arg = model_column_mock.__eq__.call_args[0]
        isinstance(call_arg, UserType)

    def test_user_type_cast_fail(self):
        class UserType:
            def __init__(self, *args, **kwargs):
                msg = "Cast failed"
                raise ValueError(msg)

        class ModelSchema(BaseModel):
            user_type: UserType
            model_config = ConfigDict(arbitrary_types_allowed=True)

        # field name for model ModelSchema
        field_name = "user_type"
        with pytest.raises(InvalidType) as exc_info:
            build_filter_expression(
                field_name=field_name,
                schema_field=ModelSchema.model_fields[field_name],
                model_column=Mock(),
                operator=Mock(),
                value=Any,
            )

        assert exc_info.value.as_dict == {
            "detail": "Can't cast filter value `typing.Any` to arbitrary type.",
            "meta": [
                {
                    "detail": "Cast failed",
                    "source": {"pointer": ""},
                    "status_code": status.HTTP_409_CONFLICT,
                    "title": "Conflict",
                },
            ],
            "status_code": status.HTTP_409_CONFLICT,
            "title": "Invalid type.",
        }
