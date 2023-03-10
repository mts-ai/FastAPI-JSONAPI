"""ORM types enums."""

from fastapi_jsonapi.data_layers.fields.enum import Enum


class DBORMType(str, Enum):
    tortoise = "tortoise"
    sqlalchemy = "sqlalchemy"


class DBORMOperandType(str, Enum):
    or_ = "or"
    and_ = "and"
    not_ = "not"
