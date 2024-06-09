"""JSON API types."""

from typing import (
    Optional,
    Union,
)

DictValueType = Union[str, int, float, dict, list]
Filters = list[dict[str, Optional[DictValueType]]]
JsonParamsType = dict[str, DictValueType]
