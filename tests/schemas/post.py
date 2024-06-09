from __future__ import annotations

from typing import (
    Annotated,
    TYPE_CHECKING,
)

from pydantic import ConfigDict
from fastapi_jsonapi.schema_base import (
    BaseModel,
)
from fastapi_jsonapi.types_metadata import RelationshipInfo

if TYPE_CHECKING:
    from tests.schemas.user import UserSchema
    from tests.schemas.post_comment import PostCommentSchema


class PostAttributesBaseSchema(BaseModel):
    title: str
    body: str
    model_config = ConfigDict(from_attributes=True)


class PostBaseSchema(PostAttributesBaseSchema):
    """Post base schema."""

    user: Annotated[
        UserSchema | None,
        RelationshipInfo(
            resource_type="user",
        ),
    ] = None
    comments: Annotated[
        list[PostCommentSchema] | None,
        RelationshipInfo(
            resource_type="post_comment",
            many=True,
        ),
    ] = None


class PostPatchSchema(PostBaseSchema):
    """Post PATCH schema."""


class PostInSchema(PostBaseSchema):
    """Post input schema."""


class PostSchema(PostInSchema):
    """Post item schema."""

    id: int
