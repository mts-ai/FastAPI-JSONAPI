from typing import Optional

from pydantic import BaseModel as PydanticBaseModel

from fastapi_jsonapi.schema_base import Field, RelationshipInfo


class BaseModel(PydanticBaseModel):
    class Config:
        orm_mode = True


class UserBaseSchema(BaseModel):
    id: int
    name: str
    bio: Optional["UserBioSchema"] = Field(
        relationship=RelationshipInfo(
            resource_type="user_bio",
        ),
    )
    computers: Optional["ComputerSchema"] = Field(
        relationship=RelationshipInfo(
            resource_type="computer",
            many=True,
        ),
    )


class UserSchema(BaseModel):
    id: int
    name: str


class UserBioBaseSchema(BaseModel):
    birth_city: str
    favourite_movies: str
    keys_to_ids_list: dict[str, list[int]] = None

    user: "UserSchema" = Field(
        relationship=RelationshipInfo(
            resource_type="user",
        ),
    )


class ComputerBaseSchema(BaseModel):
    id: int
    name: str
    user: Optional["UserSchema"] = Field(
        relationship=RelationshipInfo(
            resource_type="user",
        ),
    )
