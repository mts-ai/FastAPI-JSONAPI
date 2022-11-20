"""Functions for extracting and updating signatures."""

from collections import OrderedDict
from enum import Enum
from inspect import (
    Parameter,
    Signature,
    signature,
)
from typing import (
    Callable,
    Optional,
    Type,
    OrderedDict as OrderedDictType,
)

from fastapi import Query
from pydantic import BaseModel

from fastapi_rest_jsonapi.querystring import QueryStringManager


def is_necessary_request(func: Callable) -> bool:
    """Check request in parameters."""
    sig = signature(func)
    params_dict = OrderedDict(sig.parameters)
    return "request" in params_dict


def update_signature(
        sig: Signature,
        schema: Optional[Type[BaseModel]] = None,
        other: OrderedDictType[str, Parameter] = None,
) -> Signature:
    """
    Add docs parameters to signature.

    :params sig: сигнатура декоратора библиотеки wrapper, которая оборачивает изначальную функцию.
    :params schema: которую нужно вставить в сигнатуру.
    :params other: список параметров из начальной функции.
    """
    other: OrderedDict[str, Parameter] = other or {}
    params_dict = OrderedDict(sig.parameters)
    params_dict.pop("kwargs", None)
    params_dict.pop("cls", None)
    params_no_default = [
        i_param
        for i_name, i_param in other.items()
        if isinstance(i_param.default, type) and other[i_name].annotation is not QueryStringManager
    ]
    params_default = [
        i_param
        for i_param in other.values()
        if not isinstance(i_param.default, type)
    ]
    params: list = list(params_dict.values())
    for name, field in (schema and schema.__fields__ or {}).items():
        try:
            if field.sub_fields:
                default = Query(None, alias="filter[{alias}]".format(alias=field.alias))
                type_field = field.type_
            elif issubclass(field.type_, (dict, BaseModel)):
                continue
            elif issubclass(field.type_, Enum):
                default = Query(None, alias="filter[{alias}]".format(alias=field.alias), enum=field.type_.values())
                type_field = str
            else:
                default = Query(None, alias="filter[{alias}]".format(alias=field.alias))
                type_field = field.type_
            params.append(
                Parameter(
                    name,
                    kind=Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=Optional[type_field],
                    default=default,
                )
            )
        except Exception as ex:
            pass

    params: list = params + params_no_default + params_default
    # Убираем дубликаты
    params_dict: dict = {i_p.name: i_p for i_p in params}
    params: list = list(params_dict.values())
    params.sort(key=lambda x: not isinstance(x.default, type))

    return sig.replace(parameters=params)
