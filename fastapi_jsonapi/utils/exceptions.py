from functools import wraps

from fastapi import HTTPException, status
from pydantic import ValidationError


def handle_validation_error(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValidationError as ex:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=ex.errors(),
            )

    return wrapper
