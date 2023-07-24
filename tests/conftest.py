import asyncio
import logging

import pytest
from faker import Faker

from tests.fixtures import (  # noqa
    app,
    app_max_include_depth,
    app_plain,
    async_engine,
    async_session,
    async_session_dependency,
    async_session_plain,
    child_1,
    child_2,
    child_3,
    child_4,
    child_detail_view,
    child_list_view,
    client,
    detail_view_base_generic,
    list_view_base_generic,
    list_view_base_generic_helper_for_sqla,
    p1_c1_association,
    p1_c2_association,
    p2_c1_association,
    p2_c2_association,
    p2_c3_association,
    parent_1,
    parent_2,
    parent_3,
    parent_detail_view,
    parent_list_view,
    post_detail_view,
    post_list_view,
    sqla_uri,
    user_1,
    user_1_bio,
    user_1_comments_for_u2_posts,
    user_1_post_for_comments,
    user_1_posts,
    user_2,
    user_2_comment_for_one_u1_post,
    user_2_posts,
    user_bio_detail_view,
    user_bio_list_view,
    user_detail_view,
    user_list_view,
)

fake = Faker()


def init_tests():
    # configure_logging()
    logging.getLogger("faker.factory").setLevel(logging.INFO)


init_tests()


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
