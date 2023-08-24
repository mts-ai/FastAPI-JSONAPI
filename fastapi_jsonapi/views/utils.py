from enum import Enum
from functools import cache
from typing import Callable, Coroutine, Optional, Set, Type, Union

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
    prepare_data_layer_kwargs: Optional[Union[Callable, Coroutine]] = None

    class Config:
        arbitrary_types_allowed = True

    @property
    def handler(self) -> Optional[Union[Callable, Coroutine]]:
        return self.prepare_data_layer_kwargs
