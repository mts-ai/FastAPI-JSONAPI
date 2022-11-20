from typing import Union, Type, TypeVar
from enum import Enum as EnumOriginal

from sqlalchemy import types

from enum import Enum

from sqlalchemy.engine import Dialect


class MixinEnum(Enum):
    @classmethod
    def names(cls) -> str:
        return ",".join(x.name for x in cls)

    @classmethod
    def values(cls) -> list:
        return [value for _, value in cls._member_map_.items()]

    @classmethod
    def keys(cls) -> list:
        return [key for key, _ in cls._member_map_.items()]

    @classmethod
    def inverse(cls) -> dict:
        return {value: key for key, value in cls._member_map_.items()}

    @classmethod
    def value_to_enum(cls, value):
        _value_to_enum = {value.value: value for _, value in cls._member_map_.items()}
        return _value_to_enum.get(value)


class Enum(MixinEnum):
    pass


TypeEnum = TypeVar("TypeEnum", bound="Enum")


class EnumColumn(types.TypeDecorator):
    """
    Обычный Enum из python сохраняет в БД значение, а не ключ, как делает Enum sqlalchemy
    """

    impl = types.Text
    cache_ok = True

    def __init__(self, enum: Union[Type[EnumOriginal], Type[TypeEnum]], *args: list, **kwargs: dict):
        if not issubclass(enum, EnumOriginal):
            raise TypeError(f"{enum} is not a subtype of Enum")
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
