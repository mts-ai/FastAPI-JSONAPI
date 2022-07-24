"""W-mount schemas package."""


from .user import (
    UserJSONAPIDetailSchema,
    UserJSONAPIListSchema,
    UserJSONAPIObjectSchema,
    UserPatchJSONAPISchema,
    UserPatchSchema,
    UserPostJSONAPISchema,
    UserSchema,
)

__all__ = [
    "UserSchema",
    "UserPatchSchema",
    "UserPatchJSONAPISchema",
    "UserJSONAPIListSchema",
    "UserJSONAPIDetailSchema",
    "UserJSONAPIObjectSchema",
    "UserSchema",
    "UserPostJSONAPISchema",
]
