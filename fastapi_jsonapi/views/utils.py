from enum import Enum
from functools import cache
from typing import Callable, Optional, Set, Type

from pydantic import BaseModel


class HTTPMethod(Enum):
    ALL = "all"
    GET = "get"
    POST = "post"
    PATCH = "patch"
    DELETE = "delete"

    @cache
    def names() -> Set[str]:
        return {item.name for item in HTTPMethod}


class HTTPMethodConfig(BaseModel):
    dependencies: Optional[Type[BaseModel]] = None
    handler: Optional[Callable] = None
