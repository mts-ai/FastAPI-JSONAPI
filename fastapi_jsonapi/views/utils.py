from enum import Enum
from typing import Callable, Optional, Type, Union

from pydantic import BaseModel

ALL_METHODS = "ALL_METHODS"


class HTTPDetailMethod(Enum):
    GET = "get"
    PATCH = "patch"
    DELETE = "delete"


class HTTPListMethod(Enum):
    POST = "post"
    GET = "get"
    DELETE = "delete"


HTTPMethods = Union[HTTPDetailMethod, HTTPListMethod, ALL_METHODS]


class HTTPMethodConfig(BaseModel):
    dependencies: Optional[Type[BaseModel]] = None
    handler: Optional[Callable] = None
