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


class UserBioAttributesBaseSchema(BaseModel):
    """UserBio base schema."""

    model_config = ConfigDict(from_attributes=True)

    birth_city: str
    favourite_movies: str
    #
    # keys_to_ids_list: Optional[dict[str, list[int]]] = None


class UserBioSchema(UserBioAttributesBaseSchema):
    """UserBio item schema."""

    id: int
    user: Annotated[
        UserSchema | None,
        RelationshipInfo(
            resource_type="user",
        ),
    ] = None
