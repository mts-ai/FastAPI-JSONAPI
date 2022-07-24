"""Filters for Clickhouse."""

from typing import (
    Any,
    Dict,
    List,
    Type,
)

from pydantic import (
    BaseModel,
    Field,
)

from fastapi_rest_jsonapi.filter import json_api_filter_converter
from fastapi_rest_jsonapi.querystring import QueryStringManager


def prepare_filter_value_fo_ch(field: Type[Field], field_name: str, type_op: str, value: Any) -> Dict:
    """Prepare filter to Clickhouse request."""
    return {
        "name": field_name,
        "value": value,
        "op": type_op,
    }


async def json_api_filter_for_clickhouse(
    schema: Type[BaseModel],
    query_params: QueryStringManager,
) -> List[Dict]:
    """Convert filters for clickhouse."""
    filters = await json_api_filter_converter(
        schema=schema,
        filters=query_params.filters,
        conversion_func=prepare_filter_value_fo_ch,
    )
    return filters
