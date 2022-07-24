# fmt: off
__all__ = (
    "fake",
)
# fmt: on

from faker import Faker

fake = Faker()

Faker.seed("some-qwerty-seed-to-keep-persistent-abc-mts-pycore")
