from enum import Enum
from typing import Callable, Optional, Type, Union

from pydantic import BaseModel


class HTTPDetailMethods(Enum):
    GET = "get"
    PATCH = "patch"
    DELETE = "delete"


class HTTPListMethods(Enum):
    GET = "get"
    DELETE = "delete"


HTTPMethods = Union[HTTPDetailMethods, HTTPListMethods]


class HTTPMethodConfig(BaseModel):
    dependencies: Optional[Type[BaseModel]] = None
    handler: Optional[Callable] = None
