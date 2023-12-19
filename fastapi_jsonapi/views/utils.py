from enum import Enum
from functools import cache
from typing import Callable, Coroutine, Optional, Set, Type, Union

from pydantic import BaseModel, ConfigDict


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
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )
    dependencies: Optional[Type[BaseModel]] = None
    prepare_data_layer_kwargs: Optional[Callable] = None

    @property
    def handler(self) -> Optional[Union[Callable, Coroutine]]:
        return self.prepare_data_layer_kwargs
