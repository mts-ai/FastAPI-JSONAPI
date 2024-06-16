"""Helper to deal with querystring parameters according to jsonapi specification."""

from __future__ import annotations

from collections import defaultdict
from functools import cached_property
from typing import (
    TYPE_CHECKING,
    Any,
)
from urllib.parse import unquote

import simplejson as json
from fastapi import (
    FastAPI,
    Request,
)
from pydantic import (
    BaseModel,
    Field,
)
from starlette.datastructures import QueryParams

from fastapi_jsonapi.api import RoutersJSONAPI
from fastapi_jsonapi.exceptions import (
    BadRequest,
    InvalidField,
    InvalidFilters,
    InvalidInclude,
    InvalidSort,
    InvalidType,
)
from fastapi_jsonapi.schema import (
    get_model_field,
    get_relationship_fields_names,
)
from fastapi_jsonapi.splitter import SPLIT_REL

if TYPE_CHECKING:
    from fastapi_jsonapi.data_typing import TypeSchema


class PaginationQueryStringManager(BaseModel):
    """
    Pagination query string manager.

    Contains info about offsets, sizes, number and limits of query with pagination.
    """

    offset: int | None = None
    size: int | None = 25
    number: int = 1
    limit: int | None = None


class HeadersQueryStringManager(BaseModel):
    """
    Header query string manager.

    Contains info about request headers.
    """

    host: str | None = None
    connection: str | None = None
    accept: str | None = None
    user_agent: str | None = Field(None, alias="user-agent")
    referer: str | None = None
    accept_encoding: str | None = Field(None, alias="accept-encoding")
    accept_language: str | None = Field(None, alias="accept-language")


class QueryStringManager:
    """Querystring parser according to jsonapi reference."""

    managed_keys = ("filter", "page", "fields", "sort", "include", "q")

    def __init__(self, request: Request) -> None:
        """
        Initialize instance.

        :param request
        """
        self.request: Request = request
        self.app: FastAPI = request.app
        self.qs: QueryParams = request.query_params
        self.config: dict[str, Any] = getattr(self.app, "config", {})
        self.ALLOW_DISABLE_PAGINATION: bool = self.config.get("ALLOW_DISABLE_PAGINATION", True)
        self.MAX_PAGE_SIZE: int = self.config.get("MAX_PAGE_SIZE", 10000)
        self.MAX_INCLUDE_DEPTH: int = self.config.get("MAX_INCLUDE_DEPTH", 3)
        self.headers: HeadersQueryStringManager = HeadersQueryStringManager(**dict(self.request.headers))

    @classmethod
    def extract_item_key(cls, key: str) -> str:
        try:
            key_start = key.index("[") + 1
            key_end = key.index("]")
            return key[key_start:key_end]
        except (IndexError, ValueError):
            msg = "Parse error"
            raise BadRequest(msg, parameter=key)

    def _get_unique_key_values(self, name: str) -> dict[str, str]:
        """
        Return a dict containing key / values items for a given key, used for items like filters, page, etc.

        :param name: name of the querystring parameter
        :return: a dict of key / values items
        :raises BadRequest: if an error occurred while parsing the querystring.
        """
        results = {}

        for raw_key, value in self.qs.multi_items():
            key = unquote(raw_key)
            if not key.startswith(name):
                continue

            item_key = self.extract_item_key(key)
            results[item_key] = value

        return results

    def _get_multiple_key_values(self, name: str) -> dict[str, list]:
        results = defaultdict(list)

        for raw_key, value in self.qs.multi_items():
            key = unquote(raw_key)
            if not key.startswith(name):
                continue

            item_key = self.extract_item_key(key)
            results[item_key].extend(value.split(","))

        return results

    @classmethod
    def _simple_filters(cls, dict_: dict[str, Any]) -> list[dict[str, Any]]:
        """Filter creation."""
        return [{"name": key, "op": "eq", "val": value} for (key, value) in dict_.items()]

    @property
    def querystring(self) -> dict[str, str]:
        """
        Return original querystring but containing only managed keys.

        :return: dict of managed querystring parameter
        """
        return {
            key: value
            for (key, value) in self.qs.multi_items()
            if key.startswith(self.managed_keys) or self._get_unique_key_values("filter[")
        }

    @property
    def filters(self) -> list[dict]:
        """
        Return filters from query string.

        :return: filter information
        :raises InvalidFilters: if filter loading from json has failed.
        """
        results = []
        filters = self.qs.get("filter")
        if filters is not None:
            try:
                loaded_filters = json.loads(filters)
            except (ValueError, TypeError):
                msg = "Parse error"
                raise InvalidFilters(msg)

            if not isinstance(loaded_filters, list):
                msg = f"Incorrect filters format, expected list of conditions but got {type(loaded_filters).__name__}"
                raise InvalidFilters(msg)

            results.extend(loaded_filters)
        if filter_key_values := self._get_unique_key_values("filter["):
            results.extend(self._simple_filters(filter_key_values))
        return results

    @cached_property
    def pagination(self) -> PaginationQueryStringManager:
        """
        Return all page parameters as a dict.

        :return: a dict of pagination information.

        To allow multiples strategies, all parameters starting with `page` will be included. e.g::

            {
                "number": '25',
                "size": '150',
            }

        Example with number strategy:

            query_string = {'page[number]': '25', 'page[size]': '10'}
            parsed_query.pagination
            {'number': '25', 'size': '10'}

        :raises BadRequest: if the client is not allowed to disable pagination.
        """
        # check values type
        pagination_data: dict[str, str] = self._get_unique_key_values("page")
        pagination = PaginationQueryStringManager(**pagination_data)
        if pagination_data.get("size") is None:
            pagination.size = None
        if pagination.size:
            if self.ALLOW_DISABLE_PAGINATION is False and pagination.size == 0:
                msg = "You are not allowed to disable pagination"
                raise BadRequest(msg, parameter="page[size]")
            if self.MAX_PAGE_SIZE and pagination.size > self.MAX_PAGE_SIZE:
                pagination.size = self.MAX_PAGE_SIZE

        return pagination

    @property
    def fields(self) -> dict[str, set[Any]]:
        """
        Return fields wanted by client.

        :return: a dict of sparse fieldsets information

        Return value will be a dict containing all fields by resource, for example::

            {
                "user": ['name', 'email'],
            }

        :raises InvalidField: if result field not in schema.
        """
        fields = self._get_multiple_key_values("fields")
        for resource_type, field_names in fields.items():
            # TODO: we have registry for models (BaseModel)
            # TODO: create `type to schemas` registry

            if resource_type not in RoutersJSONAPI.all_jsonapi_routers:
                msg = f"Application has no resource with type {resource_type!r}"
                raise InvalidType(msg)

            schema: type[BaseModel] = self._get_schema(resource_type)

            for field_name in field_names:
                if field_name == "":
                    continue

                if field_name not in schema.model_fields:
                    msg = f"{schema.__name__} has no attribute {field_name}"
                    raise InvalidField(msg)

        return {resource_type: set(field_names) for resource_type, field_names in fields.items()}

    def _get_schema(self, resource_type: str) -> type[BaseModel]:
        return RoutersJSONAPI.all_jsonapi_routers[resource_type].schema

    def get_sorts(self, schema: type[TypeSchema]) -> list[dict[str, str]]:
        """
        Return fields to sort by including sort name for SQLAlchemy and row sort parameter for other ORMs.

        :return: a list of sorting information

        Example of return value::

            [
                {'field': 'created_at', 'order': 'desc'},
            ]

        :raises InvalidSort: if sort field wrong.
        """
        if not (sort_q := self.qs.get("sort")):
            return []

        sorting_results = []
        relationships_fields_names = get_relationship_fields_names(schema)

        for sort_field in sort_q.split(","):
            field = sort_field.replace("-", "")
            if SPLIT_REL not in field:
                if field not in schema.model_fields:
                    msg = f"{schema.__name__} has no attribute {field}"
                    raise InvalidSort(msg)
                if field in relationships_fields_names:
                    msg = f"You can't sort by relationship field {field!r} on {schema.__name__!r}"
                    raise InvalidSort(msg)
                field = get_model_field(schema, field)
            order = "desc" if sort_field.startswith("-") else "asc"
            sorting_results.append({"field": field, "order": order})
        return sorting_results

    @property
    def include(self) -> list[str]:
        """
        Return fields to include.

        :return: a list of include information.
        :raises InvalidInclude: if nesting is more than MAX_INCLUDE_DEPTH.
        """
        include_param: str = self.qs.get("include")
        includes = include_param.split(",") if include_param and isinstance(include_param, str) else []

        if self.MAX_INCLUDE_DEPTH is not None:
            for include_path in includes:
                if len(include_path.split(SPLIT_REL)) > self.MAX_INCLUDE_DEPTH:
                    msg = f"You can't use include through more than {self.MAX_INCLUDE_DEPTH} relationships"
                    raise InvalidInclude(msg)
        return includes
