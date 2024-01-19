from typing import Any, Union

from pydantic.fields import Field, ModelField
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.sql.elements import BinaryExpression, BooleanClauseList

from fastapi_jsonapi.schema_base import BaseModel


def jsonb_contains_sql_filter(
    schema_field: ModelField,
    model_column: InstrumentedAttribute,
    value: dict[Any, Any],
    operator: str,
) -> Union[BinaryExpression, BooleanClauseList]:
    """
    Any SQLA (or Tortoise) magic here

    :param schema_field:
    :param model_column:
    :param value: any dict
    :param operator: value 'jsonb_contains'
    :return: one sqla filter expression
    """
    return model_column.op("@>")(value)


class PictureSchema(BaseModel):
    """
    Now you can use `jsonb_contains` sql filter for this resource
    """

    name: str
    meta: dict[Any, Any] = Field(
        default_factory=dict,
        description="Any additional info in JSON format.",
        example={"location": "Moscow", "spam": "eggs"},
        _jsonb_contains_sql_filter_=jsonb_contains_sql_filter,
    )
