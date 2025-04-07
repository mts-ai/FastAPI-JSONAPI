import asyncio
import logging
from collections import defaultdict
from copy import copy

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from pytest import fixture  # noqa PT013
from pytest_asyncio import fixture as async_fixture

from fastapi_jsonapi.atomic.prepared_atomic_operation import atomic_dependency_handlers
from fastapi_jsonapi.data_layers.sqla.query_building import relationships_info_storage
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
    age_rating_g,
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
    task_1,
    task_2,
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
from tests.fixtures.views import ViewBaseGeneric  # noqa


def configure_logging():
    logging.getLogger("faker.factory").setLevel(logging.INFO)
    logging.getLogger("aiosqlite").setLevel(logging.INFO)
    # logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
    logging.basicConfig(level=logging.DEBUG)


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


@pytest.fixture
def clear_relationships_info_storage():
    data = copy(relationships_info_storage._data)
    relationships_info_storage._data = defaultdict(dict)
    yield
    relationships_info_storage._data = data


@pytest.fixture(autouse=True)
def clear_atomic_dependency_handlers():
    atomic_dependency_handlers.clear()
