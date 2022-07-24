"""Filter preparing module."""

from typing import (
    Any,
    Tuple,
    Type,
)

from pydantic.fields import ModelField

from fastapi_rest_jsonapi.schema import (
    BoolSchema,
    FloatSchema,
    IntSchema,
    StringSchema,
)
from fastapi_rest_jsonapi.exceptions import InvalidFilters
from fastapi_rest_jsonapi.splitter import prepare_field_name_for_filtering


def prepare_filter_pair(field: Type[ModelField], field_name: str, type_op: str, value: Any) -> Tuple:
    """Prepare filter."""
    name_field_q: str = prepare_field_name_for_filtering(field_name, type_op)
    return name_field_q, value


def prepare_filter_event(field: Type[ModelField], field_name: str, type_op: str, value: Any) -> dict:
    """
    Сhecking if a filter is valid for a given data type.

    :param field: field type.
    :param field_name: name of filter item.
    :param type_op: operation type in JSON API filter notation.
    :param value: value of filter item.
    :return: dict that contains info about filter name, operation, and field value.
    :raises InvalidFilters: if some operation not permitted for some data type.
    """
    if field.type_ == int and type_op not in set(IntSchema.__fields__["operation"].default):
        raise InvalidFilters(
            'Operation "{type_op}" is not permitted for type "INT"'.format(type_op=type_op), parameter=field_name
        )
    if field.type_ == float and type_op not in set(FloatSchema.__fields__["operation"].default):
        raise InvalidFilters(
            'Operation "{type_op}" is not permitted for type "FLOAT"'.format(type_op=type_op),
            parameter=field_name,
        )
    if field.type_ == str and type_op not in set(StringSchema.__fields__["operation"].default):
        raise InvalidFilters(
            'Operation "{type_op}" is not permitted for type "STRING"'.format(type_op=type_op),
            parameter=field_name,
        )
    if field.type_ == bool and type_op not in set(BoolSchema.__fields__["operation"].default):
        raise InvalidFilters(
            'Operation "{type_op}" is not permitted for type "BOOL"'.format(type_op=type_op),
            parameter=field_name,
        )
    return {
        "name": field_name,
        "op": type_op,
        "val": value,
    }
