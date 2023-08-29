import inspect
from typing import (
    Any,
    Awaitable,
    Callable,
    TypeVar,
    Union,
)

from fastapi import Request
from fastapi.dependencies.models import Dependant
from fastapi.dependencies.utils import (
    get_dependant,
    solve_dependencies,
)
from fastapi.exceptions import RequestValidationError

ReturnType = TypeVar("ReturnType")
FuncReturnType = Union[Awaitable[ReturnType], ReturnType]


class DependencyHelper:
    """
    DependencyHelper for resolving dependencies.

    Use this helper to run a func with some FastAPI Dependencies
    """

    def __init__(self, request: Request):
        self.request = request

    async def solve_dependencies_and_run(self, dependant: Dependant) -> ReturnType:
        body_data = await self.request.body() or None
        body = body_data and (await self.request.json())
        values, errors, *_ = await solve_dependencies(  # WPS110
            request=self.request,
            dependant=dependant,
            body=body,
        )

        if errors:
            raise RequestValidationError(errors, body=body)

        orig_func: Callable[..., FuncReturnType[Any]] = dependant.call  # type: ignore
        if inspect.iscoroutinefunction(orig_func):
            function_call_result = await orig_func(**values)
        else:
            function_call_result = orig_func(**values)

        return function_call_result

    async def run(self, func: Callable[..., FuncReturnType[Any]]) -> ReturnType:
        dependant = get_dependant(
            path=self.request.url.path,
            call=func,
        )

        return await self.solve_dependencies_and_run(dependant)
