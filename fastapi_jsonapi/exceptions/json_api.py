"""JSON API exceptions schemas."""

from http import HTTPStatus
from typing import (
    List,
    Optional,
)

from fastapi import HTTPException as FastApiHttpException


class HTTPException(FastApiHttpException):
    """Base HTTP Exception class customized for json_api exceptions."""

    def __init__(
        self,
        detail: str = "",
        pointer: str = "",
        parameter: str = "",
        status_code: int = HTTPStatus.BAD_REQUEST,
        title: str = "",
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
        if not errors:
            if pointer:
                pointer = pointer if pointer.startswith("/") else "/data/" + pointer
                self.source = {"pointer": pointer}
            elif parameter:
                self.source = {"parameter": parameter}
            else:
                self.source = {"pointer": ""}

            self.status_code = HTTPStatus(int(status_code))
            self.title = title or self.status_code.phrase
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


class UnsupportedFeatureORM(HTTPException):
    """Unsupported feature ORM exception class customized for json_api exceptions."""

    def __init__(
        self,
        detail: str = "",
        status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR,
        parameter: str = "",
    ):
        """
        Init for invalid ORM exception.

        :param detail: a human-readable explanation specific to this occurrence of the problem
        :param parameter: a string indicating which URI query parameter caused the error
        :param status_code: the HTTP status code applicable to this problem
        """
        super().__init__(
            detail=detail,
            parameter=parameter,
            title="Invalid server.",
            status_code=status_code,
        )


class BadRequest(HTTPException):
    """Bad request HTTP exception class customized for json_api exceptions."""

    def __init__(
        self,
        detail: str = "",
        pointer: str = "",
        parameter: str = "",
        title: str = "",
    ):
        """
        Init bad request HTTP exception.

        :param detail: a human-readable explanation specific to this occurrence of the problem
        :param pointer:  a JSON Pointer
        :param parameter: a string indicating which URI query parameter caused the error
        :param title: a short, human-readable summary of the problem
        """
        super().__init__(
            detail=detail,
            pointer=pointer,
            parameter=parameter,
            title=title,
            status_code=HTTPStatus.BAD_REQUEST,
        )


class InvalidSort(HTTPException):
    """Customized Exception for invalid sort."""

    def __init__(
        self,
        detail: str = "",
        status_code: int = HTTPStatus.BAD_REQUEST,
        parameter: str = "sort",
    ):
        """
        Init for invalid sort exception.

        :param detail: a human-readable explanation specific to this occurrence of the problem
        :param parameter: a string indicating which URI query parameter caused the error
        :param status_code: the HTTP status code applicable to this problem
        """
        super().__init__(
            detail=detail,
            parameter=parameter,
            title="Invalid sort querystring parameter.",
            status_code=status_code,
        )


class InvalidFilters(HTTPException):
    """Customized Exception for invalid filters."""

    def __init__(
        self,
        detail: str = "",
        status_code: int = HTTPStatus.BAD_REQUEST,
        parameter: str = "filters",
    ):
        """
        Invalid filters querystring parameter.

        :param detail: a human-readable explanation specific to this occurrence of the problem
        :param parameter: a string indicating which URI query parameter caused the error
        :param status_code: the HTTP status code applicable to this problem
        """
        super().__init__(
            detail=detail,
            title="Invalid filters querystring parameter.",
            parameter=parameter,
            status_code=status_code,
        )


class InvalidField(HTTPException):
    """Customized Exception for invalid field."""

    def __init__(
        self,
        detail: str = "",
        status_code: int = HTTPStatus.BAD_REQUEST,
        parameter: str = "fields",
    ):
        """
        Invalid fields querystring parameter.

        :param detail: a human-readable explanation specific to this occurrence of the problem
        :param parameter: a string indicating which URI query parameter caused the error
        :param status_code: the HTTP status code applicable to this problem
        """
        super().__init__(
            detail=detail,
            title="Invalid fields querystring parameter.",
            parameter=parameter,
            status_code=status_code,
        )


class InvalidInclude(HTTPException):
    """Customized Exception for invalid include."""

    def __init__(
        self,
        detail: str = "",
        status_code: int = HTTPStatus.BAD_REQUEST,
        parameter: str = "include",
    ):
        """
        Invalid include querystring parameter.

        :param detail: a human-readable explanation specific to this occurrence of the problem
        :param parameter: a string indicating which URI query parameter caused the error
        :param status_code: the HTTP status code applicable to this problem
        """
        super().__init__(
            detail=detail,
            title="Invalid include querystring parameter.",
            parameter=parameter,
            status_code=status_code,
        )


class InvalidType(HTTPException):
    """Error to warn that there is a conflit between resource types"""

    def __init__(
        self,
        detail: str = "",
        status_code: int = HTTPStatus.CONFLICT,
        parameter: str = "",
    ):
        """
        Error to warn that there is a conflit between resource types.

        :param detail: a human-readable explanation specific to this occurrence of the problem
        :param parameter: a string indicating which URI query parameter caused the error
        :param status_code: the HTTP status code applicable to this problem
        """
        super().__init__(
            detail=detail,
            title="Invalid type.",
            parameter=parameter,
            status_code=status_code,
        )


class RelationNotFound(HTTPException):
    """Error to warn that a relationship is not found on a model"""

    def __init__(
        self,
        detail: str = "",
        status_code: int = HTTPStatus.NOT_FOUND,
        parameter: str = "",
    ):
        """
        Error to warn that a relationship is not found on a model.

        :param detail: a human-readable explanation specific to this occurrence of the problem
        :param parameter: a string indicating which URI query parameter caused the error
        :param status_code: the HTTP status code applicable to this problem
        """
        super().__init__(
            detail=detail,
            title="Relation not found.",
            parameter=parameter,
            status_code=status_code,
        )


class RelatedObjectNotFound(HTTPException):
    """Error to warn that a related object is not found"""

    def __init__(
        self,
        detail: str = "",
        status_code: int = HTTPStatus.NOT_FOUND,
        parameter: str = "",
    ):
        """
        Error to warn that a related object is not found.

        :param detail: a human-readable explanation specific to this occurrence of the problem
        :param parameter: a string indicating which URI query parameter caused the error
        :param status_code: the HTTP status code applicable to this problem
        """
        super().__init__(
            detail=detail,
            title="Related object not found.",
            parameter=parameter,
            status_code=status_code,
        )


class ObjectNotFound(HTTPException):
    """Error to warn that an object is not found in a database"""

    def __init__(
        self,
        detail: str = "",
        status_code: int = HTTPStatus.NOT_FOUND,
        parameter: str = "",
    ):
        """
        Error to warn that an object is not found in a database.

        :param detail: a human-readable explanation specific to this occurrence of the problem
        :param parameter: a string indicating which URI query parameter caused the error
        :param status_code: the HTTP status code applicable to this problem
        """
        super().__init__(
            detail=detail,
            title="Object not found.",
            parameter=parameter,
            status_code=status_code,
        )
