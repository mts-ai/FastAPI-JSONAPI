from random import choices
from string import ascii_letters
from unittest.mock import AsyncMock

import pytest
from fastapi import (
    Depends,
    Request,
)

from fastapi_jsonapi.utils.dependency_helper import DependencyHelper

pytestmark = pytest.mark.asyncio


class TestDependencyHelper:
    async def test_dependency_helper(self):
        header_key = "".join(choices(ascii_letters, k=10))
        header_value = "".join(choices(ascii_letters, k=12))
        data_1 = object()
        data_2 = object()
        data_3 = object()

        def sub_dependency():
            return data_1

        def some_dependency(sub_dep_1=Depends(sub_dependency)):
            return sub_dep_1

        async def some_async_dependency():
            return data_3

        def some_function(
            req: Request,
            d1_as_dep=Depends(some_dependency),
            d3_as_dep=Depends(some_async_dependency),
        ):
            return d1_as_dep, data_2, d3_as_dep, req.headers.get(header_key)

        request = Request(
            {
                "type": "http",
                "path": "/foo/bar",
                "headers": [(header_key.lower().encode("latin-1"), header_value.encode("latin-1"))],
                "query_string": "",
                "fastapi_astack": AsyncMock(),
            },
        )
        # dirty
        request._body = b""

        # prepare dependency helper
        dep_helper = DependencyHelper(request)
        # run a function with dependencies
        d1, d2, d3, h_value = await dep_helper.run(some_function)
        assert d1 is data_1
        assert d2 is data_2
        assert d3 is data_3
        assert h_value == header_value
