import asyncio
import logging

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from pytest import fixture  # noqa PT013
from pytest_asyncio import fixture as async_fixture

from tests.fixtures.app import (  # noqa
    app,
    app_plain,
)
from tests.fixtures.db_connection import (  # noqa
    async_engine,
    async_session,
    async_session_plain,
)
from tests.fixtures.entities import (  # noqa
    child_1,
    child_2,
    child_3,
    child_4,
    computer_1,
    computer_2,
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
from tests.fixtures.views import (  # noqa
    DetailViewBaseGeneric,
    ListViewBaseGeneric,
)
from tests.models import Base


def configure_logging():
    logging.getLogger("faker.factory").setLevel(logging.INFO)


configure_logging()


@pytest.fixture(scope="session")
def event_loop():
    """
    Create an instance of the default event loop for each test case.

    Why:
    https://stackoverflow.com/questions/66054356/multiple-async-unit-tests-fail-but-running-them-one-by-one-will-pass
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@async_fixture()
async def client(app: FastAPI) -> AsyncClient:  # noqa
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@async_fixture(autouse=True)
async def refresh_db(async_engine):  # noqa F811
    async with async_engine.begin() as connector:
        for table in reversed(Base.metadata.sorted_tables):
            await connector.execute(table.delete())
