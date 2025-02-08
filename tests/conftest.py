import asyncio
import logging

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from pytest_asyncio import is_async_test

from tests.fixtures.app import (  # noqa
    app,
    app_plain,
)
from tests.fixtures.db_connection import (  # noqa
    async_engine,
    async_session,
    refresh_db,
)
from tests.fixtures.entities import (  # noqa
    child_1,
    child_2,
    child_3,
    child_4,
    computer_1,
    computer_2,
    computer_factory,
    p1_c1_association,
    p1_c2_association,
    p2_c1_association,
    p2_c2_association,
    p2_c3_association,
    parent_1,
    parent_2,
    parent_3,
    user_1,
    user_1_bio,
    user_1_comments_for_u2_posts,
    user_1_post,
    user_1_post_for_comments,
    user_1_posts,
    user_2,
    user_2_bio,
    user_2_comment_for_one_u1_post,
    user_2_posts,
    user_3,
    workplace_1,
    workplace_2,
)
from tests.fixtures.user import (  # noqa
    user_attributes,
    user_attributes_factory,
)
from tests.fixtures.views import (  # noqa
    DetailViewBaseGeneric,
    ListViewBaseGeneric,
)


def configure_logging():
    logging.getLogger("faker.factory").setLevel(logging.INFO)
    logging.getLogger("aiosqlite").setLevel(logging.INFO)
    # logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
    logging.basicConfig(level=logging.DEBUG)


configure_logging()

# TODO:
#  https://pytest-asyncio.readthedocs.io/en/stable/how-to-guides/run_session_tests_in_same_loop.html


def pytest_collection_modifyitems(items):
    pytest_asyncio_tests = (item for item in items if is_async_test(item))
    session_scope_marker = pytest.mark.asyncio(loop_scope="session")
    for async_test in pytest_asyncio_tests:
        async_test.add_marker(session_scope_marker, append=False)


@pytest.fixture()
async def client(app: FastAPI) -> AsyncClient:  # noqa: F811
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
