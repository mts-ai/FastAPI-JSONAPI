from typing import Any
from unittest.mock import Mock

from fastapi import status
from pydantic import BaseModel
from pytest import raises  # noqa PT013

from fastapi_jsonapi.data_layers.filtering.sqlalchemy import Node
from fastapi_jsonapi.exceptions.json_api import InvalidType


class TestNode:
    def test_user_type_cast_success(self):
        class UserType:
            def __init__(self, *args, **kwargs):
                self.value = "success"

        class ModelSchema(BaseModel):
            user_type: UserType

            class Config:
                arbitrary_types_allowed = True

        node = Node(
            model=Mock(),
            filter_={
                "name": "user_type",
                "op": "eq",
                "val": Any,
            },
            schema=ModelSchema,
        )

        model_column_mock = Mock()
        model_column_mock.eq = lambda clear_value: clear_value

        clear_value = node.create_filter(
            schema_field=ModelSchema.__fields__["user_type"],
            model_column=model_column_mock,
            operator=Mock(),
            value=Any,
        )
        assert isinstance(clear_value, UserType)
        assert clear_value.value == "success"

    def test_user_type_cast_fail(self):
        class UserType:
            def __init__(self, *args, **kwargs):
                msg = "Cast failed"
                raise ValueError(msg)

        class ModelSchema(BaseModel):
            user_type: UserType

            class Config:
                arbitrary_types_allowed = True

        node = Node(
            model=Mock(),
            filter_=Mock(),
            schema=ModelSchema,
        )

        with raises(InvalidType) as exc_info:
            node.create_filter(
                schema_field=ModelSchema.__fields__["user_type"],
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
