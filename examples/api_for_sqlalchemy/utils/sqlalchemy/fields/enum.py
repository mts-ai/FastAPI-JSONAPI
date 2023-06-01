from enum import Enum as EnumOriginal
from typing import Type, TypeVar, Union

from sqlalchemy import types
from sqlalchemy.engine import Dialect

from fastapi_jsonapi.data_layers.fields.mixins import MixinEnum

TypeEnum = TypeVar("TypeEnum", bound=MixinEnum)


class EnumColumn(types.TypeDecorator):
    """
    Обычный Enum из python сохраняет в БД значение, а не ключ, как делает Enum sqlalchemy
    """

    impl = types.Text
    cache_ok = True

    def __init__(self, enum: Union[Type[EnumOriginal], Type[TypeEnum]], *args: list, **kwargs: dict):
        if not issubclass(enum, EnumOriginal):
            msg = f"{enum} is not a subtype of Enum"
            raise TypeError(msg)
        self.enum = enum
        super().__init__(*args, **kwargs)

    def process_bind_param(self, value: Union[Type[EnumOriginal], Type[TypeEnum]], dialect: Dialect):
        if isinstance(value, EnumOriginal) and isinstance(value.value, (str, int)):
            return value.value
        if isinstance(value, str):
            return self.enum[value].value
        return value

    def process_result_value(self, value: Union[str, int], dialect: Dialect):
        return self.enum.value_to_enum(value)
