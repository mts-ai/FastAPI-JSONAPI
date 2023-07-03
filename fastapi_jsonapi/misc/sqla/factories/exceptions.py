"""Create exceptions module."""

from typing import Type, TypeVar

from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
TypeModel = TypeVar("TypeModel", bound=Base)


class ErrorCreateObject(Exception):
    """Base create object exception."""

    def __init__(self, model: Type[TypeModel], description: str, field: str = ""):
        """For a custom exception, you can define the model and error description."""
        self.model = model
        self.message = description
        self.field = field
        self.description = description


class ExceptionBeforeCreate(Exception):
    """The exception thrown before the object was created by the factory."""

    pass


class ExceptionNotFactory(Exception):
    """The exception that is thrown when there is no factory for a given model in the store."""

    pass


class ExceptionAfterCommit(Exception):
    """The exception thrown after the object was created by the factory."""

    pass


class ExceptionBeforeCommit(Exception):
    """The exception thrown before the object was created by the factory."""

    pass
