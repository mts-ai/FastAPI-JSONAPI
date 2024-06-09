from typing import (
    Annotated,
    Any,
)

from pydantic.fields import Field

from fastapi_jsonapi.contrib.sqla.filters import sql_filter_jsonb_contains
from fastapi_jsonapi.schema_base import BaseModel


class PictureSchema(BaseModel):
    """
    Now you can use `jsonb_contains` sql filter for this resource
    """

    name: str
    meta: Annotated[
        dict[str, Any],
        sql_filter_jsonb_contains,
        Field(
            default_factory=dict,
            description="Any additional info in JSON format.",
            example={"location": "Moscow", "spam": "eggs"},
        ),
    ]
