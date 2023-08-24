"""Functions for extracting and updating signatures."""
import inspect
import logging
from enum import Enum
from inspect import Parameter
from types import GenericAlias
from typing import (
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Type,
)

from fastapi import Query
from pydantic import BaseModel as BaseModelOriginal
from pydantic.fields import ModelField

from fastapi_jsonapi.schema_base import BaseModel, registry

log = logging.getLogger(__name__)


def create_filter_parameter(name: str, field: ModelField) -> Parameter:
    if field.sub_fields:
        default = Query(None, alias="filter[{alias}]".format(alias=field.alias))
        type_field = field.type_
    elif inspect.isclass(field.type_) and issubclass(field.type_, Enum) and hasattr(field.type_, "values"):
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

    available_includes_names = []

    # TODO! ?
    schema.update_forward_refs(**registry.schemas)
    for name, field in (schema.__fields__ or {}).items():
        try:
            # skip collections
            if inspect.isclass(field.type_):
                if type(field.type_) is GenericAlias:
                    continue
                if issubclass(field.type_, (dict, list, tuple, set, Dict, List, Tuple, Set)):
                    continue
            # process inner models, find relationships
            if inspect.isclass(field.type_) and issubclass(field.type_, (BaseModel, BaseModelOriginal)):
                if field.field_info.extra.get("relationship"):
                    available_includes_names.append(name)
                else:
                    log.warning(
                        "found nested schema %s for field %r. Consider marking it as relationship",
                        field,
                        name,
                    )
                continue

            # create filter params
            parameter = create_filter_parameter(
                name=name,
                field=field,
            )
            filter_params.append(parameter)
        except Exception as ex:
            log.warning("could not create filter for field %s %s", name, field, exc_info=ex)

    if available_includes_names:
        doc_available_includes = "\n".join([f"* `{name}`" for name in available_includes_names])
        include_param = Parameter(
            "_jsonapi_include",
            kind=Parameter.POSITIONAL_OR_KEYWORD,
            annotation=Optional[str],
            default=Query(
                ",".join(available_includes_names),
                alias="include",
                description=f"Available includes:\n {doc_available_includes}",
            ),
        )
        include_params.append(include_param)
    return filter_params, include_params
