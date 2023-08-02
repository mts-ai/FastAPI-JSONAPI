"""Post Comment schemas module."""
from datetime import datetime
from typing import TYPE_CHECKING

from fastapi_jsonapi.schema_base import BaseModel, Field, RelationshipInfo

if TYPE_CHECKING:
    from .post import PostSchema
    from .user import UserSchema


class PostCommentBaseSchema(BaseModel):
    """PostComment base schema."""

    class Config:
        """Pydantic schema config."""

        orm_mode = True

    text: str
    created_at: datetime = Field(description="Create datetime")
    modified_at: datetime = Field(description="Update datetime")

    post: "PostSchema" = Field(
        relationship=RelationshipInfo(
            resource_type="post",
        ),
    )
    author: "UserSchema" = Field(
        relationship=RelationshipInfo(
            resource_type="user",
        ),
    )


class PostCommentPatchSchema(PostCommentBaseSchema):
    """PostComment PATCH schema."""


class PostCommentInSchema(PostCommentBaseSchema):
    """PostComment input schema."""


class PostCommentSchema(PostCommentInSchema):
    """PostComment item schema."""

    class Config:
        """Pydantic model config."""

        orm_mode = True

    id: int
