"""User base schemas module."""

from datetime import datetime
from typing import Optional, TYPE_CHECKING, List

from fastapi_rest_jsonapi.schema_base import BaseModel, Field, RelationshipInfo

from examples.api_for_sqlalchemy.models.enums import UserStatusEnum

if TYPE_CHECKING:
    from .post import PostSchema


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
    status: UserStatusEnum = Field(default=UserStatusEnum.active)


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
    posts: List["PostSchema"] = Field(
        relationship=RelationshipInfo(
            resource_type="post",
            many=True,
        ),
    )
