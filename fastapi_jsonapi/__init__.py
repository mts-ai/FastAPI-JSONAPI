"""JSON API utils package."""

from fastapi import FastAPI

from fastapi_jsonapi.api import RoutersJSONAPI
from fastapi_jsonapi.exceptions import BadRequest
from fastapi_jsonapi.exceptions.handlers import base_exception_handler
from fastapi_jsonapi.exceptions.json_api import HTTPException
from fastapi_jsonapi.querystring import QueryStringManager

__version__ = "2.4.2"

__all__ = [
    "init",
    "BadRequest",
    "QueryStringManager",
    "RoutersJSONAPI",
]


def init(app: FastAPI):
    """
    Init the app.

    Processes the application by setting the entities necessary for work.

    Action list:
    - Registers default exception handlers for exceptions defined
      in "fastapi_jsonapi.exceptions" module.
    """
    app.add_exception_handler(HTTPException, base_exception_handler)
