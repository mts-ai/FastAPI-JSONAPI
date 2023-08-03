from enum import Enum
from typing import Callable, Optional, Type, Union

from pydantic import BaseModel

ALL_METHODS = "ALL_METHODS"


class HTTPDetailMethods(Enum):
    GET = "get"
    PATCH = "patch"
    DELETE = "delete"


class HTTPListMethods(Enum):
    POST = "post"
    GET = "get"
    DELETE = "delete"


HTTPMethods = Union[HTTPDetailMethods, HTTPListMethods, ALL_METHODS]


class HTTPMethodConfig(BaseModel):
    dependencies: Optional[Type[BaseModel]] = None
    handler: Optional[Callable] = None
