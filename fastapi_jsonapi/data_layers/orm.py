"""ORM types enums."""

from fastapi_jsonapi.data_layers.fields.enum import Enum


class DBORMOperandType(str, Enum):  # noqa: SLOT000
    or_ = "or"
    and_ = "and"
    not_ = "not"
