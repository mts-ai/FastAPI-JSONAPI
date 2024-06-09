from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel as PydanticBaseModel, ConfigDict

from fastapi_jsonapi.types_metadata import RelationshipInfo


class BaseModel(PydanticBaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserBaseSchema(BaseModel):
    id: int
    name: str
    bio: Annotated[
        UserBioSchema | None,
        RelationshipInfo(
            resource_type="user_bio",
        ),
    ]
    computers: Annotated[
        ComputerSchema | None,
        RelationshipInfo(
            resource_type="computer",
            many=True,
        ),
    ]


class UserSchema(BaseModel):
    id: int
    name: str


class UserBioSchema(BaseModel):
    birth_city: str
    favourite_movies: str
    # keys_to_ids_list: Optional[dict[str, list[int]]] = None

    user: Annotated[
        UserSchema | None,
        RelationshipInfo(
            resource_type="user",
        ),
    ]


class ComputerSchema(BaseModel):
    id: int
    name: str
    user: Annotated[
        UserSchema | None,
        RelationshipInfo(
            resource_type="user",
        ),
    ]
