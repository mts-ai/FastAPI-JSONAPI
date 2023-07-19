"""ORM types enums."""

from fastapi_jsonapi.data_layers.fields.enum import Enum


class DBORMOperandType(str, Enum):
    or_ = "or"
    and_ = "and"
    not_ = "not"
