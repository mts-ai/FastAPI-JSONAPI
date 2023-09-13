"""User schemas module."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from examples.api_for_sqlalchemy.models.enums import UserStatusEnum
from fastapi_jsonapi.schema_base import BaseModel, Field, RelationshipInfo

if TYPE_CHECKING:
    from .computer import ComputerSchema
    from .post import PostSchema
    from .user_bio import UserBioSchema


class UserBaseSchema(BaseModel):
    """User base schema."""

    class Config:
        """Pydantic schema config."""

        orm_mode = True

    class Enum:
        """User enums."""

        status = UserStatusEnum

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    age: Optional[int] = None
    status: UserStatusEnum = Field(default=UserStatusEnum.active)
    email: str | None = None

    posts: Optional[List["PostSchema"]] = Field(
        relationship=RelationshipInfo(
            resource_type="post",
            many=True,
        ),
    )

    bio: Optional["UserBioSchema"] = Field(
        relationship=RelationshipInfo(
            resource_type="user_bio",
        ),
    )

    computers: Optional[List["ComputerSchema"]] = Field(
        relationship=RelationshipInfo(
            resource_type="computer",
            many=True,
        ),
    )


class UserPatchSchema(UserBaseSchema):
    """User PATCH schema."""


class UserInSchema(UserBaseSchema):
    """User input schema."""


class UserSchema(UserInSchema):
    """User item schema."""

    class Config:
        """Pydantic model config."""

        orm_mode = True

    id: int
    created_at: datetime = Field(description="Create datetime")
    modified_at: datetime = Field(description="Update datetime")
