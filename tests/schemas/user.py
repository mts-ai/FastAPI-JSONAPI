from __future__ import annotations

from typing import (
    Optional,
    Annotated,
    TYPE_CHECKING,
)

from fastapi_jsonapi.types_metadata import ClientCanSetId
from pydantic import ConfigDict

from fastapi_jsonapi.schema_base import BaseModel
from fastapi_jsonapi.types_metadata import RelationshipInfo

if TYPE_CHECKING:
    from tests.schemas import (
        PostSchema,
        UserBioSchema,
        ComputerSchema,
        WorkplaceSchema,
    )


class UserAttributesBaseSchema(BaseModel):
    name: str
    age: Optional[int] = None
    email: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class UserBaseSchema(UserAttributesBaseSchema):
    """User base schema."""

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

    workplace: Annotated[
        WorkplaceSchema | None,
        RelationshipInfo(
            resource_type="workplace",
        ),
    ] = None


class UserPatchSchema(UserBaseSchema):
    """User PATCH schema."""


class UserInSchema(UserBaseSchema):
    """User input schema."""


class UserInSchemaAllowIdOnPost(UserBaseSchema):
    # TODO: handle non-instance
    id: Annotated[str, ClientCanSetId()]


class UserSchema(UserInSchema):
    """User item schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int


class CustomUserAttributesSchema(UserBaseSchema):
    spam: str
    eggs: str
