"""Pagination utils module."""

from typing import (
    Any,
    Optional,
    Tuple,
)

from fastapi_rest_jsonapi.querystring import (
    PaginationQueryStringManager,
    QueryStringManager,
)


async def get_pagination_params(pagination: PaginationQueryStringManager) -> Tuple[Optional[int], Optional[int]]:
    """Get pagination parameters."""
    offset = None
    if pagination.offset is None and pagination.size is not None and pagination.number is not None:
        offset = pagination.size * (pagination.number - 1)

    limit = None
    if pagination.limit is None and pagination.size:
        limit = pagination.size

    return limit, offset


async def json_api_pagination(query, query_params: QueryStringManager) -> Tuple[Any, int, int]:
    """Filter data according to pagination parameters."""
    total_pages: int = 1
    count: int = await query.count()
    limit, offset = await get_pagination_params(query_params.pagination)

    if offset:
        query = query.offset(offset)

    if limit:
        query = query.limit(limit)
        total_pages = count // limit + 1

    return query, total_pages, count
