"""Functions for extracting and updating signatures."""
import inspect
import logging
from enum import Enum
from inspect import Parameter
from typing import (
    Optional,
    Type,
)

from fastapi import Query
from pydantic.fields import FieldInfo

from fastapi_jsonapi.schema_base import BaseModel, registry

log = logging.getLogger(__name__)


def create_filter_parameter(name: str, field: FieldInfo) -> Parameter:
    if hasattr(field, "sub_fields") and field.sub_fields:
        default = Query(None, alias="filter[{alias}]".format(alias=field.alias))
        type_field = field.annotation
    elif (
        inspect.isclass(field.annotation)
        and issubclass(field.annotation, Enum)
        and hasattr(field.annotation, "values")
    ):
        default = Query(None, alias="filter[{alias}]".format(alias=field.alias), enum=field.annotation.values())
        type_field = str
    else:
        default = Query(None, alias="filter[{alias}]".format(alias=field.alias))
        type_field = field.annotation

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
    schema.model_rebuild(_types_namespace=registry.schemas)
    for name, field in (schema.model_fields or {}).items():
        try:
            try:
                if field.json_schema_extra.get("relationship"):
                    available_includes_names.append(name)
                    continue
                else:
                    log.warning(
                        "found nested schema %s for field %r. Consider marking it as relationship",
                        field,
                        name,
                    )
            except AttributeError:
                pass

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
