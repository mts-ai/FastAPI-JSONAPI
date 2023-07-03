"""Base updater exception module."""


class ErrorUpdateObject(Exception):
    """Base updater exception."""

    def __init__(self, model, description, field: str = ""):
        """When creating an exception object for an updater, you must specify the model and error description."""
        self.model = model
        self.message = description
        self.field = field
        self.description = description


class ExceptionBeforeUpdate(Exception):
    """The exception thrown before the object was updated by the updater."""

    pass


class ObjectNotFound(ErrorUpdateObject):
    """The exception if the object was not found."""

    pass


class ExceptionNotUpdater(Exception):
    """Raise exception if updater not found in storage."""

    pass
