"""User base schemas module."""

from datetime import datetime
from typing import Optional

from pydantic import (
    BaseModel,
    Field,
)

from examples.api_for_tortoise_orm.models.enums import UserStatusEnum


class UserBaseSchema(BaseModel):
    """User base schema."""

    class Config(object):
        """Pydantic schema config."""

        orm_mode = True

    class Enum(object):
        """Device enums."""

        status = UserStatusEnum


class UserPatchSchema(UserBaseSchema):
    """User PATCH schema."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    status: UserStatusEnum = Field(default=UserStatusEnum.active)


class UserInSchema(UserBaseSchema):
    """User input schema."""

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    status: UserStatusEnum = Field(default=UserStatusEnum.active)


class UserSchema(UserInSchema):
    """User item schema."""

    class Config(object):
        """Pydantic model config."""

        orm_mode = True
        model = "users"

    id: int
    created_at: datetime = Field(description="Время создания данных")
    modified_at: datetime = Field(description="Время изменения данных")
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    status: UserStatusEnum = Field(default=UserStatusEnum.active)
