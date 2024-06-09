"""User schemas module."""
from __future__ import annotations

from datetime import datetime
from typing import (
    TYPE_CHECKING,
    List,
    Annotated,
)
from pydantic import ConfigDict

from fastapi_jsonapi.schema_base import BaseModel, Field, RelationshipInfo
from fastapi_jsonapi.schema_base import BaseModel, Field
from fastapi_jsonapi.types_metadata import RelationshipInfo

if TYPE_CHECKING:
    from .computer import ComputerSchema
    from .post import PostSchema
    from .user_bio import UserBioSchema


class UserBaseSchema(BaseModel):
    """User base schema."""

    model_config = ConfigDict(from_attributes=True)

    class Enum:
        """User enums."""

        status = UserStatusEnum

    status: UserStatusEnum = Field(default=UserStatusEnum.active)
    first_name: str | None = None
    last_name: str | None = None
    age: int | None = None
    email: str | None = None

    posts: Annotated[
        list[PostSchema] | None,
        RelationshipInfo(
            resource_type="post",
            many=True,
        ),
    ] = None

    bio: Annotated[
        UserBioSchema | None,
        RelationshipInfo(
            resource_type="user_bio",
        ),
    ] = None

    computers: Annotated[
        list[ComputerSchema] | None,
        RelationshipInfo(
            resource_type="computer",
            many=True,
        ),
    ] = None


class UserPatchSchema(UserBaseSchema):
    """User PATCH schema."""


class UserInSchema(UserBaseSchema):
    """User input schema."""


class UserSchema(UserInSchema):
    """User item schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime = Field(description="Create datetime")
    modified_at: datetime = Field(description="Update datetime")
