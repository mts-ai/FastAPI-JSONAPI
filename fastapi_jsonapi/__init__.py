"""JSON API utils package."""

from fastapi_jsonapi.api import RoutersJSONAPI
from fastapi_jsonapi.data_layers.sqlalchemy_engine import SqlalchemyDataLayer
from fastapi_jsonapi.data_layers.tortoise_orm_engine import TortoiseDataLayer
from fastapi_jsonapi.exceptions import BadRequest
from fastapi_jsonapi.querystring import QueryStringManager

__version__ = "1.1.0"

__all__ = [
    "BadRequest",
    "SqlalchemyDataLayer",
    "TortoiseDataLayer",
    "QueryStringManager",
    "RoutersJSONAPI",
]
