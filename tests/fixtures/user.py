import pytest

from tests.misc.utils import fake
from tests.schemas import UserAttributesBaseSchema


@pytest.fixture()
def user_attributes_factory():
    def factory():
        return UserAttributesBaseSchema(
            name=fake.name(),
            age=fake.pyint(min_value=13, max_value=99),
            email=fake.email(),
        )

    return factory


@pytest.fixture()
def user_attributes(user_attributes_factory):
    return user_attributes_factory()
