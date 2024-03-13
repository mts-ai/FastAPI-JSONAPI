from __future__ import annotations

from collections import defaultdict
from enum import Enum
from functools import cache
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Coroutine,
    Dict,
    Iterable,
    List,
    Optional,
    Set,
    Type,
    Union,
)

from pydantic import BaseModel
from pydantic.fields import ModelField

from fastapi_jsonapi.data_typing import TypeSchema
from fastapi_jsonapi.schema import JSONAPIObjectSchema
from fastapi_jsonapi.schema_builder import (
    JSONAPIResultDetailSchema,
    JSONAPIResultListSchema,
)

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

    @cache
    def names() -> Set[str]:
        return {item.name for item in HTTPMethod}


class HTTPMethodConfig(BaseModel):
    dependencies: Optional[Type[BaseModel]] = None
    prepare_data_layer_kwargs: Optional[Union[Callable, Coroutine]] = None

    class Config:
        arbitrary_types_allowed = True

    @property
    def handler(self) -> Optional[Union[Callable, Coroutine]]:
        return self.prepare_data_layer_kwargs


def _get_includes_indexes_by_type(included: List[JSONAPIObjectSchema]) -> Dict[str, List[int]]:
    result = defaultdict(list)

    for idx, item in enumerate(included):
        result[item.type].append(idx)

    return result


# TODO: move to schema builder?
def _is_relationship_field(field: ModelField) -> bool:
    return "relationship" in field.field_info.extra


def _get_schema_field_names(schema: Type[TypeSchema]) -> Set[str]:
    """
    Returns all attribute names except relationships
    """
    result = set()

    for field_name, field in schema.__fields__.items():
        if _is_relationship_field(field):
            continue

        result.add(field_name)

    return result


def _get_exclude_fields(
    schema: Type[TypeSchema],
    include_fields: Iterable[str],
) -> Set[str]:
    schema_fields = _get_schema_field_names(schema)

    if IGNORE_ALL_FIELDS_LITERAL in include_fields:
        return schema_fields

    return set(_get_schema_field_names(schema)).difference(include_fields)


def _calculate_exclude_fields(
    response: JSONAPIResponse,
    query_params: QueryStringManager,
    jsonapi: RoutersJSONAPI,
) -> Dict:
    included = "included" in response.__fields__ and response.included or []
    is_list_response = isinstance(response, JSONAPIResultListSchema)

    exclude_params: Dict[str, Any] = {}

    includes_indexes_by_type = _get_includes_indexes_by_type(included)

    for resource_type, field_names in query_params.fields.items():
        schema = jsonapi.all_jsonapi_routers[resource_type]._schema
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
) -> Union[JSONAPIResponse, Dict]:
    if not query_params.fields:
        return response

    exclude_params = _calculate_exclude_fields(response, query_params, jsonapi)

    if exclude_params:
        return response.dict(exclude=exclude_params, by_alias=True)

    return response
