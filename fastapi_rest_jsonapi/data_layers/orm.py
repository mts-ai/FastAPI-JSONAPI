"""ORM types enums."""

from fastapi_rest_jsonapi.data_layers.fields.enum import Enum


class DBORMType(str, Enum):
    clickhouse = "clickhouse"
    tortoise = "tortoise"
    filter_event = "filter_event"


class DBORMOperandType(str, Enum):
    or_ = "or"
    and_ = "and"
    not_ = "not"
