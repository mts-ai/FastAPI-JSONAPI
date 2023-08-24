from fastapi import Request
from fastapi.responses import JSONResponse

from fastapi_jsonapi.exceptions import HTTPException


async def base_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"errors": [exc.as_dict]},
    )
