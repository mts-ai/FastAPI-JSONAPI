from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Annotated,
)

from pydantic import ConfigDict

from fastapi_jsonapi.schema_base import (
    BaseModel,
)
from fastapi_jsonapi.types_metadata import RelationshipInfo

if TYPE_CHECKING:
    from tests.schemas import PostSchema, UserSchema


class PostCommentAttributesBaseSchema(BaseModel):
    text: str
    model_config = ConfigDict(from_attributes=True)


class PostCommentBaseSchema(PostCommentAttributesBaseSchema):
    """PostComment base schema."""

    post: Annotated[
        # PostSchema | None,
        PostSchema,
        RelationshipInfo(
            resource_type="post",
        ),
    ]
    author: Annotated[
        # UserSchema | None,
        UserSchema,
        RelationshipInfo(
            resource_type="user",
        ),
    ]


class PostCommentSchema(PostCommentBaseSchema):
    """PostComment item schema."""

    id: int
