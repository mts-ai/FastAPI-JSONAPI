"""When you'll need to patch faker, do it here."""

from faker import Faker
from faker.providers import lorem

fake = Faker()
fake.add_provider(lorem)

__all__ = ["fake"]
