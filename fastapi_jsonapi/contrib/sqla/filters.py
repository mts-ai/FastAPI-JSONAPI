from typing import (
    TYPE_CHECKING,
    cast,
)

from sqlalchemy import (
    BinaryExpression,
    BooleanClauseList,
    func,
)
from sqlalchemy.orm import InstrumentedAttribute

from fastapi_jsonapi.types_metadata import CustomFilterSQL

if TYPE_CHECKING:
    from pydantic.fields import FieldInfo


SQLAExpressionType = BinaryExpression | BooleanClauseList


class CustomFilterSQLA(CustomFilterSQL[InstrumentedAttribute, SQLAExpressionType]):
    """Base class for custom SQLAlchemy filters"""


class LowerEqualsFilterSQL(CustomFilterSQLA):
    def get_expression(
        self,
        schema_field: "FieldInfo",
        model_column: InstrumentedAttribute,
        value: str,
        operator: str,
    ) -> BinaryExpression:
        return cast(
            BinaryExpression,
            func.lower(model_column) == func.lower(value),
        )


# TODO: tests coverage
class JSONBContainsFilterSQL(CustomFilterSQLA):
    def get_expression(
        self,
        schema_field: "FieldInfo",
        model_column: InstrumentedAttribute,
        value: str,
        operator: str,
    ) -> BinaryExpression:
        return model_column.op("@>")(value)


sql_filter_lower_equals = LowerEqualsFilterSQL(op="lower_equals")
sql_filter_jsonb_contains = JSONBContainsFilterSQL(op="jsonb_contains")
