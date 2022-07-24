"""Навешиваем сортировки подготовленные по спецификации JSON:API."""
from tortoise.queryset import QuerySet

from typing import Optional

from fastapi_rest_jsonapi.querystring import QueryStringManager


def json_api_sort(
    query,
    query_params: QueryStringManager,
    default_sort: Optional[str] = None,
) -> QuerySet:
    """
    Реализация динамической сортировки для query в tortoise.

    :param query: запрос
    :param query_params: параметры от клиента
    :param default_sort: дефолтная сортировка, например "-id" или `sort=-id,created_at`
    """
    if query_params.sorting:
        for i_sort in query_params.sorting:
            i_order = "" if i_sort["order"] == "asc" else "-"
            i_field = "{order}{field}".format(order=i_order, field=i_sort["field"])
            query = query.order_by(i_field)
    elif default_sort:
        query = query.order_by(default_sort)
    return query
