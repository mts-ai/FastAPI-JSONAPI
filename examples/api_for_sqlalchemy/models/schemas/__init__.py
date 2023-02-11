"""schemas package."""


from .user import (
    UserSchema,
    UserInSchema,
    UserPatchSchema,
)

from .post import (
    PostSchema,
    PostInSchema,
    PostPatchSchema,
)


__all__ = [
    "UserSchema",
    "UserInSchema",
    "UserPatchSchema",
    "PostSchema",
    "PostInSchema",
    "PostPatchSchema",
]
