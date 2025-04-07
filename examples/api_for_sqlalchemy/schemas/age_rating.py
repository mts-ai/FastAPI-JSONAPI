from typing import TYPE_CHECKING, Annotated, Optional

from annotated_types import MaxLen, MinLen
from pydantic import ConfigDict

from fastapi_jsonapi.schema_base import BaseModel
from fastapi_jsonapi.types_metadata import RelationshipInfo

name_constrained = Annotated[
    str,
    MinLen(1),
    MaxLen(20),
]

if TYPE_CHECKING:
    from examples.api_for_sqlalchemy.schemas.movie import MovieSchema


class AgeRatingAttributesSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )
    name: str
    description: str


class AgeRatingBaseSchema(AgeRatingAttributesSchema):
    movies: Annotated[
        Optional[list["MovieSchema"]],
        RelationshipInfo(
            resource_type="movie",
            many=True,
        ),
    ] = None


class AgeRatingCreateSchema(AgeRatingBaseSchema):
    name: name_constrained


class AgeRatingUpdateSchema(AgeRatingBaseSchema):
    name: Optional[name_constrained] = None
    description: Optional[str] = None


class AgeRatingSchema(AgeRatingBaseSchema):
    """
    Age Rating
    """
