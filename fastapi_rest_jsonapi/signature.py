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
)

from fastapi import Query
from pydantic import BaseModel


def is_necessary_request(func: Callable) -> bool:
    """Check request in parameters."""
    sig = signature(func)
    params_dict = OrderedDict(sig.parameters)
    return "request" in params_dict


def update_signature(sig: Signature, schema: Type[BaseModel]) -> Signature:
    """Add docs parameters to signature."""
    params_dict = OrderedDict(sig.parameters)
    params_dict.pop("kwargs", None)
    params_dict.pop("cls", None)
    params: list = list(params_dict.values())
    for name, field in schema.__fields__.items():
        try:
            if issubclass(field.type_, (dict, BaseModel)):
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
    return sig.replace(parameters=params)
