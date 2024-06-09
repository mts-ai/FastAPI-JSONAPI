from typing import (
    Generic,
    TypeVar,
    TYPE_CHECKING,
)

from dataclasses import dataclass

if TYPE_CHECKING:
    # noinspection PyProtectedMember
    from pydantic.fields import FieldInfo


ColumnType = TypeVar("ColumnType")
ExpressionType = TypeVar("ExpressionType")


@dataclass(frozen=True)
class CustomFilterSQL(Generic[ColumnType, ExpressionType]):
    op: str

    def get_expression(
        self,
        schema_field: "FieldInfo",
        model_column: ColumnType,
        value: str,
        operator: str,
    ) -> ExpressionType:
        raise NotImplementedError
