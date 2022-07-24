"""User schemas package."""

from .base import (
    UserInSchema,
    UserPatchSchema,
    UserSchema,
)
from .json_api import (
    UserJSONAPIDetailSchema,
    UserJSONAPIListSchema,
    UserJSONAPIObjectSchema,
    UserPatchJSONAPISchema,
    UserPostJSONAPISchema,
)

__all__ = [
    "UserSchema",
    "UserInSchema",
    "UserPatchSchema",
    "UserJSONAPIObjectSchema",
    "UserJSONAPIDetailSchema",
    "UserJSONAPIListSchema",
    "UserPatchJSONAPISchema",
    "UserPostJSONAPISchema",
]
