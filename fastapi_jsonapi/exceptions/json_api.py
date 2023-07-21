"""JSON API exceptions schemas."""

from http import HTTPStatus
from typing import (
    List,
    Optional,
)

from fastapi import HTTPException as FastApiHttpException
from fastapi import status


class HTTPException(FastApiHttpException):
    """Base HTTP Exception class customized for json_api exceptions."""

    title: str = ""
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    parameter: str = ""

    def __init__(
        self,
        detail: str = "",
        pointer: str = "",
        parameter: str = "",
        title: Optional[str] = None,
        status_code: Optional[int] = None,
        errors: Optional[List["HTTPException"]] = None,
    ):
        """
        Init base HTTP exception.

        :param detail: a human-readable explanation specific to this occurrence of the problem
        :param pointer:  a JSON Pointer
        :param parameter: a string indicating which URI query parameter caused the error
        :param status_code: the HTTP status code applicable to this problem
        :param title: a short, human-readable summary of the problem
        :param errors: may be passed over other arguments as list of `HTTPException` objects
        """
        if status_code is not None:
            self.status_code = status_code

        if title is not None:
            self.title = title

        parameter = parameter or self.parameter
        if not errors:
            if pointer:
                pointer = pointer if pointer.startswith("/") else "/data/" + pointer
                self.source = {"pointer": pointer}
            elif parameter:
                self.source = {"parameter": parameter}
            else:
                self.source = {"pointer": ""}

            self.status_code = int(self.status_code)
            self.title = self.title or HTTPStatus(self.status_code).phrase
            self._detail = detail

            errors = [self]

        super().__init__(errors[0].status_code, {"errors": [error._dict for error in errors]})

    @property
    def _dict(self):
        return {
            "status_code": self.status_code,
            "source": self.source,
            "title": self.title,
            "detail": self._detail,
        }


class InternalServerError(HTTPException):
    """
    Verbose name, it's the same as HTTP Exception
    """

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR


class UnsupportedFeatureORM(InternalServerError):
    """
    Unsupported feature ORM exception class customized for json_api exceptions.
    Init for invalid ORM exception.
    """

    title = "Unsupported ORM"


class BadRequest(HTTPException):
    """
    Bad request HTTP exception class customized for json_api exceptions.

    Init bad request HTTP exception.
    """

    status_code = status.HTTP_400_BAD_REQUEST


class NotFound(BadRequest):
    """
    Error to warn that a relationship is not found on a model
    """

    status_code = status.HTTP_404_NOT_FOUND


class InvalidSort(BadRequest):
    """Customized Exception for invalid sort."""

    title = "Invalid sort querystring parameter."
    parameter: str = "sort"


class InvalidFilters(BadRequest):
    """Customized Exception for invalid filters."""

    title = "Invalid filters querystring parameter."
    parameter: str = "filters"


class InvalidField(BadRequest):
    """
    Customized Exception for invalid field.

    Invalid fields querystring parameter.
    """

    title = "Invalid fields querystring parameter."
    parameter: str = "fields"


class InvalidInclude(BadRequest):
    """
    Customized Exception for invalid include.

    Invalid include querystring parameter.
    """

    title = "Invalid include querystring parameter."
    parameter: str = "include"


class InvalidType(HTTPException):
    """
    Error to warn that there is a conflit between resource types

    Error to warn that there is a conflict between resource types.
    """

    title = "Invalid type."
    status_code = status.HTTP_409_CONFLICT


class RelationNotFound(NotFound):
    """
    Error to warn that a relationship is not found on a model
    """

    title = "Relation not found."


class RelatedObjectNotFound(NotFound):
    """Error to warn that a related object is not found"""

    title = "Related object not found."


class ObjectNotFound(NotFound):
    """Error to warn that an object is not found in a database"""

    title = "Resource not found."

    @property
    def _dict(self):
        return {
            "status_code": self.status_code,
            "meta": self.source,
            "title": self.title,
            "detail": self._detail,
        }
