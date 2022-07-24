"""JSON API types."""

from typing import (
    Dict,
    List,
    Optional,
    Union,
)

DictValueType = Union[str, int, float, dict, list]
Filters = List[Dict[str, Optional[DictValueType]]]
JsonParamsType = Dict[str, DictValueType]
