from typing import Optional

from pydantic import BaseModel as PydanticBaseModel, ConfigDict

from fastapi_jsonapi.schema_base import Field, RelationshipInfo


class BaseModel(PydanticBaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserBaseSchema(BaseModel):
    id: int
    name: str
    bio: Optional["UserBioSchema"] = Field(
        json_schema_extra={
            "relationship": RelationshipInfo(
                resource_type="user_bio",
            ),
        },
    )
    computers: Optional["ComputerSchema"] = Field(
        json_schema_extra={
            "relationship": RelationshipInfo(
                resource_type="computer",
                many=True,
            ),
        },
    )


class UserSchema(BaseModel):
    id: int
    name: str


class UserBioBaseSchema(BaseModel):
    birth_city: str
    favourite_movies: str
    # keys_to_ids_list: Optional[dict[str, list[int]]] = None

    user: "UserSchema" = Field(
        json_schema_extra={
            "relationship": RelationshipInfo(
                resource_type="user",
            ),
        },
    )


class ComputerBaseSchema(BaseModel):
    id: int
    name: str
    user: Optional["UserSchema"] = Field(
        json_schema_extra={
            "relationship": RelationshipInfo(
                resource_type="user",
            ),
        },
    )
