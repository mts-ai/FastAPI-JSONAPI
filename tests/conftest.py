import asyncio
import logging

import pytest
from faker import Faker

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
