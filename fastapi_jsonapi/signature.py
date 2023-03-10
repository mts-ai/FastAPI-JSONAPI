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
    Dict,
    List,
    Optional,
    Set,
    Type,
    OrderedDict as OrderedDictType,
)

from fastapi import Query
from pydantic import BaseModel
from starlette.requests import Request

from fastapi_jsonapi.querystring import QueryStringManager


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
    params_dict = OrderedDict(sig.parameters)

    other_: OrderedDict[str, Parameter] = (other or {}).copy()
    for i_k, i_v in (other or {}).items():
        for j_k, j_v in params_dict.items():
            try:
                if i_v.annotation is j_v.annotation.__fields__["attributes"].type_:
                    other_.pop(i_k)
            except Exception:
                pass
            try:
                if i_v.annotation is Request:
                    other_.pop(i_k)
            except Exception:
                pass
            try:
                if i_v.annotation is QueryStringManager:
                    other_.pop(i_k)
            except Exception:
                pass
    other = other_

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
            if issubclass(field.type_, (dict, BaseModel, list, set, List, Set, Dict)):
                continue
            elif field.sub_fields:
                default = Query(None, alias="filter[{alias}]".format(alias=field.alias))
                type_field = field.type_
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
