from typing import cast

from sqlalchemy import func
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy import BinaryExpression

from fastapi_jsonapi.types_metadata import CustomFilterSQL
from pydantic.fields import FieldInfo


class LowerEqualsFilterSQL(CustomFilterSQL[InstrumentedAttribute, BinaryExpression]):
    def get_expression(
        self,
        schema_field: FieldInfo,
        model_column: InstrumentedAttribute,
        value: str,
        operator: str,
    ) -> BinaryExpression:
        return cast(
            BinaryExpression,
            func.lower(model_column) == func.lower(value),
        )


sql_filter_lower_equals = LowerEqualsFilterSQL(op="lower_equals")
