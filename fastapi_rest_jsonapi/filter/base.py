"""Base filters creator."""

from typing import (
    Any,
    Dict,
    List,
    Optional,
    Union,
)

from tortoise.expressions import Q

from fastapi_rest_jsonapi.data_layers.orm import (
    DBORMOperandType,
    DBORMType,
)
from fastapi_rest_jsonapi.exceptions import QueryError
from fastapi_rest_jsonapi.data_layers.fields.enum import Enum


def val_to_query(val: Any) -> Any:
    """Value to query."""
    if isinstance(val, Enum):
        val = val.value
    return val


def create_q_tortoise(filter_q: Union[tuple, Q]) -> Q:
    """Tortoise filter creation."""
    if isinstance(filter_q, tuple):
        return Q(**{filter_q[0]: filter_q[1]})
    else:
        return Q(filter_q)


def validate_q_tortoise(filter_q: Union[None, Q, Dict[str, Union[Q, List[Q]]]]) -> Optional[Q]:
    """
    Tortoise filter validation.

    :param filter_q: dict with filter body.
    :return: validated filter.
    :raises QueryError: if the field in the filter does not match the field in tortoise.
    """
    if isinstance(filter_q, Q):
        return Q(filter_q)
    elif filter_q is None:
        return None
    else:
        raise QueryError("An unexpected argument for Q (result_filter={type})".format(type=type(filter_q)))


def orm_and_or(db_type: DBORMType, op: DBORMOperandType, filters: list) -> Union[None, Q, Dict[str, Union[Q, List[Q]]]]:
    """Filter for query to ORM."""
    # TODO: add clickhouse
    if not filters:
        return None
    if db_type is DBORMType.tortoise:
        if op is DBORMOperandType.or_:
            result_filter = None
            for i_filter in filters:
                i_filter = i_filter[0] if isinstance(i_filter, list) else i_filter
                if result_filter is None:
                    result_filter = create_q_tortoise(i_filter)
                else:
                    result_filter |= create_q_tortoise(i_filter)
            return result_filter
        if op is DBORMOperandType.and_:
            result_filter = None
            for i_filter in filters:
                i_filter = i_filter[0] if isinstance(i_filter, list) else i_filter
                if result_filter is None:
                    result_filter = create_q_tortoise(i_filter)
                else:
                    result_filter &= create_q_tortoise(i_filter)
            return result_filter
        if op is DBORMOperandType.not_:
            return ~Q(**{filters[0][0][0]: filters[0][0][1]})
    elif db_type is DBORMType.clickhouse:
        pass
    elif db_type is DBORMType.filter_event:
        if op is DBORMOperandType.or_:
            return {"or": filters}
        if op is DBORMOperandType.and_:
            return {"and": filters}
        if op is DBORMOperandType.not_:
            return {"not": filters[0]}
    return None
