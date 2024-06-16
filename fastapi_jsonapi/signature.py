import inspect
import logging
from enum import Enum
from inspect import Parameter
from typing import (
    TYPE_CHECKING,
    Optional,
)

from fastapi import Query

from fastapi_jsonapi.common import get_relationship_info_from_field_metadata
from fastapi_jsonapi.schema_base import (
    BaseModel,
)

if TYPE_CHECKING:
    # noinspection PyProtectedMember
    from pydantic.fields import FieldInfo


log = logging.getLogger(__name__)


def create_filter_parameter(
    name: str,
    field: "FieldInfo",
) -> Parameter:
    filter_alias = field.alias or name
    query_filter_name = f"filter[{filter_alias}]"
    if (
        inspect.isclass(field.annotation)
        and issubclass(field.annotation, Enum)
        and hasattr(field.annotation, "values")
    ):
        # TODO: enum handling? what if is optional?
        default = Query(
            None,
            alias=query_filter_name,
            # todo: read from annotation or somehow else?
            enum=list(field.annotation),
        )
        type_field = str
    else:
        default = Query(None, alias=query_filter_name)
        type_field = field.annotation

    return Parameter(
        name=name,
        kind=Parameter.POSITIONAL_OR_KEYWORD,
        annotation=Optional[type_field],
        default=default,
    )


def get_param_for_includes(
    includes_names: list[str],
) -> Parameter:
    doc_available_includes = "\n".join([f"* `{name}`" for name in includes_names])
    return Parameter(
        "_jsonapi_include",
        kind=Parameter.POSITIONAL_OR_KEYWORD,
        annotation=Optional[str],
        default=Query(
            ",".join(includes_names),
            alias="include",
            description=f"Available includes:\n {doc_available_includes}",
        ),
    )


def create_additional_query_params(schema: type[BaseModel]) -> tuple[list[Parameter], list[Parameter]]:
    filter_params = []
    include_params = []
    if not schema:
        return filter_params, include_params

    available_includes_names = []

    # TODO: annotation? why `model_fields` is underlined in PyCharm?
    for name, field in schema.model_fields.items():
        if get_relationship_info_from_field_metadata(field):
            available_includes_names.append(name)
        else:
            parameter = create_filter_parameter(
                name=name,
                field=field,
            )
            filter_params.append(parameter)

    if available_includes_names:
        include_param = get_param_for_includes(available_includes_names)
        include_params.append(include_param)
    return filter_params, include_params
