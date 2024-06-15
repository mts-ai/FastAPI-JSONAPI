"""Helper to create sqlalchemy sortings according to filter querystring parameter"""

from __future__ import annotations

from fastapi_jsonapi.data_layers.node_shared import Node
from fastapi_jsonapi.data_layers.shared import create_filters_or_sorts
from fastapi_jsonapi.data_typing import TypeModel, TypeSchema


def create_sorts(model: type[TypeModel], filter_info: list | dict, schema: type[TypeSchema]):
    """
    Apply filters from filters information to base query.

    :params model: the model of the node.
    :params filter_info: current node filter information.
    :params schema: the resource.
    """
    return create_filters_or_sorts(model, filter_info, Node, schema)
