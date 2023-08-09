from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from fastapi_jsonapi.exceptions import HTTPException


async def base_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"errors": [exc._dict]},
    )


def register_exception_handlers(app: FastAPI, exclude_exception_handlers: Optional[list] = None):
    """
    Registers default exception handlers for exceptions defined in "fastapi_jsonapi.exceptions" module.
    If you want to override one or many of handlers you may disable them with "exclude_exception_handlers" arg.
    This is a function list that contains the set of handlers to disable.

    Example:
    -------
    >>> from fastapi_jsonapi.exceptions.handlers import base_exception_handler
    >>> app: FastAPI
    >>> register_exception_handlers(app, exclude_exception_handlers=[base_exception_handler])
        ↑
    The "object_not_found_exception_handler" disabled in this point.
    """
    exclude_exception_handlers = exclude_exception_handlers or []

    if base_exception_handler not in exclude_exception_handlers:
        app.add_exception_handler(HTTPException, base_exception_handler)
