from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi_jsonapi.data_layers.filtering.sqlalchemy import Node as NodeSQLAlchemy
    from fastapi_jsonapi.data_typing import TypeModel, TypeSchema


def create_filters_or_sorts(
    model: type[TypeModel],
    filter_or_sort_info: list | dict,
    class_node: type[NodeSQLAlchemy],
    schema: type[TypeSchema],
) -> tuple:
    """
    Apply filters / sorts from filters / sorts information to base query

    :param model: the model of the node
    :param filter_or_sort_info: current node filter_or_sort information
    :param class_node:
    :param schema: the resource
    """
    filters_or_sorts = []
    joins = []
    for filter_or_sort in filter_or_sort_info:
        filters_or_sort, join = class_node(model, filter_or_sort, schema).resolve()
        filters_or_sorts.append(filters_or_sort)
        joins.extend(join)

    return filters_or_sorts, joins
