"""Json api filters module."""

from typing import (
    Any,
    Callable,
    Dict,
    List,
    Type,
    Union,
)

from pydantic import BaseModel
from pydantic.fields import ModelField
from tortoise.queryset import QuerySet

from fastapi_rest_jsonapi.data_layers.orm import (
    DBORMOperandType,
    DBORMType,
)
from fastapi_rest_jsonapi.exceptions import InvalidFilters
from fastapi_rest_jsonapi.filter.base import (
    orm_and_or,
    val_to_query,
)
from fastapi_rest_jsonapi.filter.preparing import prepare_filter_pair
from fastapi_rest_jsonapi.querystring import QueryStringManager


async def json_api_filter_converter(
    schema: Type[BaseModel],
    filters: List[dict],  # TODO: signature changed, be aware
    conversion_func: Callable,
    db_type: DBORMType = DBORMType.tortoise,
) -> List:
    """
    Make a list with filters, which can be used in the tortoise filter.

    :param schema: pydantic schema of object.
    :param filters: list of JSON API filters.
    :param conversion_func: conversion function.
    :param db_type: type of database.
    :return: list of filters, prepared for use in tortoise model.
    :raises InvalidFilters: if the filter was created with an error.
    """
    converted_filters: List = []
    for i_filter in filters:
        if "or" in i_filter:
            result = await json_api_filter_converter(schema, i_filter["or"], conversion_func, db_type)
            converted_filters.append(orm_and_or(db_type, DBORMOperandType.or_, result))
            continue
        elif "and" in i_filter:
            result = await json_api_filter_converter(schema, i_filter["and"], conversion_func, db_type)
            converted_filters.append(orm_and_or(db_type, DBORMOperandType.and_, result))
            continue
        elif "not" in i_filter:
            result = await json_api_filter_converter(schema, [i_filter["not"]], conversion_func, db_type)
            converted_filters.append(orm_and_or(db_type, DBORMOperandType.not_, result))
            continue
        model_fields = i_filter["name"].split(".")
        name_field: str = model_fields[0]
        if len(model_fields) > 1:
            result = await json_api_filter_converter(
                schema.__fields__[name_field].type_,
                [
                    {
                        "name": ".".join(model_fields[1:]),
                        "op": i_filter["op"],
                        "val": i_filter["val"],
                    }
                ],
                conversion_func,
                db_type,
            )
            converted_filters.append(result)
        else:
            val: Union[List[Any], Any]
            field: ModelField = schema.__fields__[name_field]
            if isinstance(i_filter["val"], list) and field.type_ is not list:
                val = _validate_filters(i_filter, field)
            else:
                val, errors = field.validate(i_filter["val"], {}, loc=field.alias)
                val = val_to_query(val)
                if errors:
                    raise InvalidFilters(str(errors), parameter=field.alias)
            converted_filters.append(conversion_func(field, name_field, i_filter["op"], val))
    return converted_filters


def _validate_filters(json_api_filter: Dict[str, List[str]], model_filed: ModelField) -> List:
    val = []
    for i_v in json_api_filter["val"]:
        i_val, errors = model_filed.validate(i_v, {}, loc=model_filed.alias)
        if errors:
            raise InvalidFilters(str(errors), parameter=model_filed.alias)
        i_val = val_to_query(i_val)
        val.append(i_val)
    return val


async def json_api_filter(
    query,
    schema: Type[BaseModel],
    query_params: QueryStringManager,
) -> QuerySet:
    """Make queries with filtering from request."""
    filters = await json_api_filter_converter(
        schema=schema,
        filters=query_params.filters,
        conversion_func=prepare_filter_pair,
    )
    for i_filter in filters:
        query = query.filter(**{i_filter[0]: i_filter[1]})
    return query
