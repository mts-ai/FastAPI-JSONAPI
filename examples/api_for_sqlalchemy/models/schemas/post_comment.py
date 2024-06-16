from __future__ import annotations

from datetime import datetime
from typing import (
    TYPE_CHECKING,
    Annotated,
)

from pydantic import ConfigDict

from fastapi_jsonapi.schema_base import (
    BaseModel,
    Field,
)
from fastapi_jsonapi.types_metadata import RelationshipInfo

if TYPE_CHECKING:
    from .post import PostSchema
    from .user import UserSchema


class PostCommentBaseSchema(BaseModel):
    """PostComment base schema."""

    model_config = ConfigDict(from_attributes=True)

    text: str
    created_at: datetime = Field(description="Create datetime")
    modified_at: datetime = Field(description="Update datetime")

    post: Annotated[
        PostSchema | None,
        RelationshipInfo(
            resource_type="post",
        ),
    ] = None
    author: Annotated[
        UserSchema | None,
        RelationshipInfo(
            resource_type="user",
        ),
    ] = None


class PostCommentPatchSchema(PostCommentBaseSchema):
    """PostComment PATCH schema."""


class PostCommentInSchema(PostCommentBaseSchema):
    """PostComment input schema."""


class PostCommentSchema(PostCommentInSchema):
    """PostComment item schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
