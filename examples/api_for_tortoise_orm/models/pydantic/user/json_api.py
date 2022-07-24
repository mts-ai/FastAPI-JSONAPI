"""User JSON API schemas module."""

from typing import (
    List,
    Optional,
)

from pydantic import (
    BaseModel,
    Field,
)

from fastapi_rest_jsonapi.schema import JSONAPIResultListMetaSchema, JSONAPIResultListJSONAPISchema
from .base import (
    UserInSchema,
    UserPatchSchema,
    UserSchema,
)


class UserPatchJSONAPISchema(BaseModel):
    """User PATCH JSON API schema."""

    id: int
    type: str = Field(default="usesr", description="Тип ресурса")
    attributes: UserPatchSchema


class UserPostJSONAPISchema(BaseModel):
    """User POST JSON API schema."""

    id: Optional[int] = None
    type: str = Field(default="users", description="Тип ресурса")
    attributes: UserInSchema


class UserJSONAPIObjectSchema(BaseModel):
    """User object JSON API schema."""

    id: int
    type: str = Field(default="users", description="Тип ресурса")
    attributes: UserSchema


class UserJSONAPIListSchema(BaseModel):
    """User list JSON API schema."""

    meta: Optional[JSONAPIResultListMetaSchema] = Field(description="Meta данные json-api")
    jsonapi: JSONAPIResultListJSONAPISchema = JSONAPIResultListJSONAPISchema()
    data: List[UserJSONAPIObjectSchema]


class UserJSONAPIDetailSchema(BaseModel):
    """Device detail JSON API schema."""

    meta: Optional[JSONAPIResultListMetaSchema] = Field(description="Meta данные json-api")
    jsonapi: JSONAPIResultListJSONAPISchema = JSONAPIResultListJSONAPISchema()
    data: UserJSONAPIObjectSchema
