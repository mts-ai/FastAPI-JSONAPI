from dataclasses import dataclass
from typing import (
    Any,
    Callable,
)


@dataclass(frozen=True)
class ClientCanSetId:
    cast_type: Callable[[Any], Any] | None = None
