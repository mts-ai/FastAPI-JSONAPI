"""Functions for extracting and updating signatures."""

import logging
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
    Tuple,
    ForwardRef,
)

from fastapi import Query
from pydantic.fields import ModelField
from starlette.requests import Request

from fastapi_rest_jsonapi.querystring import QueryStringManager
from fastapi_rest_jsonapi.schema_base import BaseModel, registry

log = logging.getLogger(__name__)


def create_filter_parameter(name: str, field: ModelField) -> Parameter:
    if field.sub_fields:
        default = Query(None, alias="filter[{alias}]".format(alias=field.alias))
        type_field = field.type_
    elif issubclass(field.type_, Enum) and hasattr(field.type_, "values"):
        default = Query(None, alias="filter[{alias}]".format(alias=field.alias), enum=field.type_.values())
        type_field = str
    else:
        default = Query(None, alias="filter[{alias}]".format(alias=field.alias))
        type_field = field.type_

    return Parameter(
        name,
        kind=Parameter.POSITIONAL_OR_KEYWORD,
        annotation=Optional[type_field],
        default=default,
    )


def create_additional_query_params(schema: Optional[Type[BaseModel]]) -> tuple[list[Parameter], list[Parameter]]:
    filter_params = []
    include_params = []
    if not schema:
        return filter_params, include_params

    # TODO! ?
    schema.update_forward_refs(**registry.schemas)
    for name, field in (schema.__fields__ or {}).items():
        # skip collections
        if issubclass(field.type_, (dict, list, tuple, set, Dict, List, Tuple, Set)):
            continue
        try:
            # process inner models, find relationships
            if issubclass(field.type_, BaseModel):
                if field.field_info.extra.get("relationship"):
                    # TODO?
                    # build enum?
                    pass
                    # parameter = create_include_parameter(name=name, field=field)
                    # include_params.append(parameter)
                else:
                    log.warning("found nested schema %s for field %r. Consider marking it as relationship", field, name)
                continue

            # create filter params
            parameter = create_filter_parameter(
                name=name,
                field=field,
            )
            filter_params.append(parameter)
        except Exception as ex:
            log.warning("could not create filter for field %s %s", name, field, exc_info=ex)

    include_param = Parameter(
        "_jsonapi_include",
        kind=Parameter.POSITIONAL_OR_KEYWORD,
        annotation=Optional[str],
        default=Query(None, alias="include"),
    )
    include_params.append(include_param)
    return filter_params, include_params


def update_signature(
    sig: Signature,
    schema: Optional[Type[BaseModel]] = None,
    other: OrderedDictType[str, Parameter] = None,
    exclude_filters: bool = False,
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
    params_default = [i_param for i_param in other.values() if not isinstance(i_param.default, type)]
    params = list(params_dict.values())
    filter_params, include_params = create_additional_query_params(schema=schema)
    params = params + ([] if exclude_filters else filter_params) + include_params + params_no_default + params_default
    # Убираем дубликаты
    params_dict: dict = {i_p.name: i_p for i_p in params}
    params: list = list(params_dict.values())
    params.sort(key=lambda x: not isinstance(x.default, type))

    return sig.replace(parameters=params)
