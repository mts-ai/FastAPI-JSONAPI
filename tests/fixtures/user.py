import pytest

from tests.misc.utils import fake
from tests.schemas import UserAttributesBaseSchema


@pytest.fixture()
def user_attributes():
    user_attributes = UserAttributesBaseSchema(
        name=fake.name(),
        age=fake.pyint(),
    )
    return user_attributes
