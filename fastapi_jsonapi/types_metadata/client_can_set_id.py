from typing import (
    Callable,
    Any,
)

from dataclasses import dataclass


@dataclass(frozen=True)
class ClientCanSetId:
    cast_type: Callable[[Any], Any] | None = None
