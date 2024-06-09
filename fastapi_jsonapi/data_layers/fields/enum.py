"""Base enum module."""

from fastapi_jsonapi.data_layers.fields.mixins import (
    MixinEnum,
    MixinIntEnum,
)


class Enum(MixinEnum):
    """
    Base enum class.

    All used non-integer enumerations must inherit from this class.
    """


class IntEnum(MixinIntEnum):
    """
    Base IntEnum class.

    All used integer enumerations must inherit from this class.
    """
