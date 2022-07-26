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
        model = "users"

    id: int
    created_at: datetime = Field(description="Время создания данных")
    modified_at: datetime = Field(description="Время изменения данных")
