from datetime import date
from typing import (
    TYPE_CHECKING,
    Annotated,
    Optional,
)

from annotated_types import MaxLen, MinLen
from pydantic import ConfigDict

from fastapi_jsonapi.schema_base import BaseModel
from fastapi_jsonapi.types_metadata import RelationshipInfo

if TYPE_CHECKING:
    from examples.api_for_sqlalchemy.schemas.age_rating import AgeRatingSchema

title_constrained = Annotated[
    str,
    MinLen(1),
    MaxLen(120),
]


class MovieAttributesSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )
    title: str
    description: str
    age_rating: Optional[str] = None


class MovieBaseSchema(MovieAttributesSchema):
    age_rating_obj: Annotated[
        Optional["AgeRatingSchema"],
        RelationshipInfo(
            resource_type="age-rating",
            resource_id_example="PG-13",
            id_field_name="name",
        ),
    ] = None


class MovieCreateSchema(MovieBaseSchema):
    """
    Create
    """

    title: title_constrained


class MovieUpdateSchema(MovieBaseSchema):
    title: Optional[title_constrained] = None
    description: Optional[str] = None
    release_date: Optional[date] = None
    duration: Optional[int] = None


class MovieSchema(MovieBaseSchema):
    id: int
