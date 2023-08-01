"""JSON API utils package."""

from fastapi_jsonapi.api import RoutersJSONAPI
from fastapi_jsonapi.exceptions import BadRequest
from fastapi_jsonapi.querystring import QueryStringManager

__version__ = "1.1.0"

__all__ = [
    "BadRequest",
    "QueryStringManager",
    "RoutersJSONAPI",
]
