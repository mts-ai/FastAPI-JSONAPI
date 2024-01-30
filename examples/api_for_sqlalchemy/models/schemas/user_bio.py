"""User Bio schemas module."""

from datetime import datetime
from typing import TYPE_CHECKING, Dict, List

from pydantic import ConfigDict

from fastapi_jsonapi.schema_base import BaseModel, Field, RelationshipInfo

if TYPE_CHECKING:
    from .user import UserSchema


class UserBioBaseSchema(BaseModel):
    """UserBio base schema."""

    model_config = ConfigDict(from_attributes=True)

    birth_city: str
    favourite_movies: str
    keys_to_ids_list: Dict[str, List[int]] = None

    user: "UserSchema" = Field(
        relationship=RelationshipInfo(
            resource_type="user",
        ),
    )


class UserBioPatchSchema(UserBioBaseSchema):
    """UserBio PATCH schema."""


class UserBioInSchema(UserBioBaseSchema):
    """UserBio input schema."""


class UserBioSchema(UserBioInSchema):
    """UserBio item schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime = Field(description="Create datetime")
    modified_at: datetime = Field(description="Update datetime")
