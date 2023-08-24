"""Helper to deal with querystring parameters according to jsonapi specification."""
from functools import cached_property
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Type,
    Union,
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

from fastapi_jsonapi.exceptions import (
    BadRequest,
    InvalidField,
    InvalidFilters,
    InvalidInclude,
    InvalidSort,
)
from fastapi_jsonapi.schema import (
    get_model_field,
    get_relationships,
    get_schema_from_type,
)
from fastapi_jsonapi.splitter import SPLIT_REL

if TYPE_CHECKING:
    from fastapi_jsonapi.data_typing import TypeSchema


class PaginationQueryStringManager(BaseModel):
    """
    Pagination query string manager.

    Contains info about offsets, sizes, number and limits of query with pagination.
    """

    offset: Optional[int] = None
    size: Optional[int] = 25
    number: int = 1
    limit: Optional[int] = None


class HeadersQueryStringManager(BaseModel):
    """
    Header query string manager.

    Contains info about request headers.
    """

    host: Optional[str] = None
    connection: Optional[str] = None
    accept: Optional[str] = None
    user_agent: Optional[str] = Field(None, alias="user-agent")
    referer: Optional[str] = None
    accept_encoding: Optional[str] = Field(None, alias="accept-encoding")
    accept_language: Optional[str] = Field(None, alias="accept-language")


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
        self.config: Dict[str, Any] = getattr(self.app, "config", {})
        self.ALLOW_DISABLE_PAGINATION: bool = self.config.get("ALLOW_DISABLE_PAGINATION", True)
        self.MAX_PAGE_SIZE: int = self.config.get("MAX_PAGE_SIZE", 10000)
        self.MAX_INCLUDE_DEPTH: int = self.config.get("MAX_INCLUDE_DEPTH", 3)
        self.headers: HeadersQueryStringManager = HeadersQueryStringManager(**dict(self.request.headers))

    def _get_key_values(self, name: str) -> Dict[str, Union[List[str], str]]:
        """
        Return a dict containing key / values items for a given key, used for items like filters, page, etc.

        :param name: name of the querystring parameter
        :return: a dict of key / values items
        :raises BadRequest: if an error occurred while parsing the querystring.
        """
        results: Dict[str, Union[List[str], str]] = {}

        for raw_key, value in self.qs.multi_items():
            key = unquote(raw_key)
            try:
                if not key.startswith(name):
                    continue

                key_start = key.index("[") + 1
                key_end = key.index("]")
                item_key = key[key_start:key_end]

                if "," in value:
                    results.update({item_key: value.split(",")})
                else:
                    results.update({item_key: value})
            except Exception:
                msg = "Parse error"
                raise BadRequest(msg, parameter=key)

        return results

    @classmethod
    def _simple_filters(cls, dict_: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Filter creation."""
        return [{"name": key, "op": "eq", "val": value} for (key, value) in dict_.items()]

    @property
    def querystring(self) -> Dict[str, str]:
        """
        Return original querystring but containing only managed keys.

        :return: dict of managed querystring parameter
        """
        return {
            key: value
            for (key, value) in self.qs.multi_items()
            if key.startswith(self.managed_keys) or self._get_key_values("filter[")
        }

    @property
    def filters(self) -> List[dict]:
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
        if self._get_key_values("filter["):
            results.extend(self._simple_filters(self._get_key_values("filter[")))
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
        pagination_data: Dict[str, Union[List[str], str]] = self._get_key_values("page")
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

    # TODO: finally use this! upgrade Sqlachemy Data Layer
    #  and add to all views (get list/detail, create, patch)
    @property
    def fields(self) -> Dict[str, List[str]]:
        """
        Return fields wanted by client.

        :return: a dict of sparse fieldsets information

        Return value will be a dict containing all fields by resource, for example::

            {
                "user": ['name', 'email'],
            }

        :raises InvalidField: if result field not in schema.
        """
        if self.request.method != "GET":
            msg = "attribute 'fields' allowed only for GET-method"
            raise InvalidField(msg)
        fields = self._get_key_values("fields")
        for key, value in fields.items():
            if not isinstance(value, list):
                value = [value]  # noqa: PLW2901
                fields[key] = value
            # TODO: we have registry for models (BaseModel)
            # TODO: create `type to schemas` registry
            schema: Type[BaseModel] = get_schema_from_type(key, self.app)
            for field in value:
                if field not in schema.__fields__:
                    msg = "{schema} has no attribute {field}".format(
                        schema=schema.__name__,
                        field=field,
                    )
                    raise InvalidField(msg)

        return fields

    def get_sorts(self, schema: Type["TypeSchema"]) -> List[Dict[str, str]]:
        """
        Return fields to sort by including sort name for SQLAlchemy and row sort parameter for other ORMs.

        :return: a list of sorting information

        Example of return value::

            [
                {'field': 'created_at', 'order': 'desc'},
            ]

        :raises InvalidSort: if sort field wrong.
        """
        if sort_q := self.qs.get("sort"):
            sorting_results = []
            for sort_field in sort_q.split(","):
                field = sort_field.replace("-", "")
                if SPLIT_REL not in field:
                    if field not in schema.__fields__:
                        msg = "{schema} has no attribute {field}".format(
                            schema=schema.__name__,
                            field=field,
                        )
                        raise InvalidSort(msg)
                    if field in get_relationships(schema):
                        msg = "You can't sort on {field} because it is a relationship field".format(field=field)
                        raise InvalidSort(msg)
                    field = get_model_field(schema, field)
                order = "desc" if sort_field.startswith("-") else "asc"
                sorting_results.append({"field": field, "order": order})
            return sorting_results

        return []

    @property
    def include(self) -> List[str]:
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
                    msg = "You can't use include through more than {max_include_depth} relationships".format(
                        max_include_depth=self.MAX_INCLUDE_DEPTH,
                    )
                    raise InvalidInclude(msg)
        return includes
