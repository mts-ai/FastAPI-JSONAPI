from __future__ import annotations

from collections import defaultdict
from collections.abc import Coroutine, Iterable
from enum import Enum
from functools import cache
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Union,
)

from pydantic import BaseModel, ConfigDict

from fastapi_jsonapi.common import get_relationship_info_from_field_metadata
from fastapi_jsonapi.schema_builder import (
    JSONAPIResultDetailSchema,
    JSONAPIResultListSchema,
)
from fastapi_jsonapi.data_typing import TypeSchema
from fastapi_jsonapi.schema import JSONAPIObjectSchema

if TYPE_CHECKING:
    from fastapi_jsonapi.api import RoutersJSONAPI
    from fastapi_jsonapi.querystring import QueryStringManager


JSONAPIResponse = Union[JSONAPIResultDetailSchema, JSONAPIResultListSchema]
IGNORE_ALL_FIELDS_LITERAL = ""


class HTTPMethod(Enum):
    ALL = "all"
    GET = "get"
    POST = "post"
    PATCH = "patch"
    DELETE = "delete"

    @staticmethod
    @cache
    def names() -> set[str]:
        return {item.name for item in HTTPMethod}


class HTTPMethodConfig(BaseModel):
    dependencies: type[BaseModel] | None = None
    prepare_data_layer_kwargs: Callable | None = None
    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def handler(self) -> Callable | Coroutine | None:
        return self.prepare_data_layer_kwargs


def get_includes_indexes_by_type(included: list[JSONAPIObjectSchema]) -> dict[str, list[int]]:
    result = defaultdict(list)

    for idx, item in enumerate(included):
        result[item.type].append(idx)

    return result


def get_schema_field_names(schema: type[TypeSchema]) -> set[str]:
    """Returns all attribute names except relationships"""
    result = set()

    for field_name, field in schema.__fields__.items():
        if get_relationship_info_from_field_metadata(field):
            continue

        result.add(field_name)

    return result


def _get_exclude_fields(
    schema: type[TypeSchema],
    include_fields: Iterable[str],
) -> set[str]:
    schema_fields = get_schema_field_names(schema)

    if IGNORE_ALL_FIELDS_LITERAL in include_fields:
        return schema_fields

    return set(get_schema_field_names(schema)).difference(include_fields)


def _calculate_exclude_fields(
    response: JSONAPIResponse,
    query_params: QueryStringManager,
    jsonapi: RoutersJSONAPI,
) -> dict:
    included = "included" in response.__fields__ and response.included or []
    is_list_response = isinstance(response, JSONAPIResultListSchema)

    exclude_params: dict[str, Any] = {}

    includes_indexes_by_type = get_includes_indexes_by_type(included)

    for resource_type, field_names in query_params.fields.items():
        schema = jsonapi.all_jsonapi_routers[resource_type].schema
        exclude_fields = _get_exclude_fields(schema, include_fields=field_names)
        attributes_exclude = {"attributes": exclude_fields}

        if resource_type == jsonapi.type_:
            if is_list_response:
                exclude_params["data"] = {"__all__": attributes_exclude}
            else:
                exclude_params["data"] = attributes_exclude

            continue

        if not included:
            continue

        target_type_indexes = includes_indexes_by_type.get(resource_type)

        if target_type_indexes:
            if "included" not in exclude_params:
                exclude_params["included"] = {}

            exclude_params["included"].update((idx, attributes_exclude) for idx in target_type_indexes)

    return exclude_params


def handle_jsonapi_fields(
    response: JSONAPIResponse,
    query_params: QueryStringManager,
    jsonapi: RoutersJSONAPI,
) -> JSONAPIResponse | dict:
    if not query_params.fields:
        return response

    exclude_params = _calculate_exclude_fields(response, query_params, jsonapi)

    if exclude_params:
        return response.dict(exclude=exclude_params, by_alias=True)

    return response
