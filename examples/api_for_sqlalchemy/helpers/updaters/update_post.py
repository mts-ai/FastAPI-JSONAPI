"""Update user helper."""

from typing import (
    Any,
    Dict,
    Union,
)

from fastapi_rest_jsonapi.querystring import HeadersQueryStringManager
from .exceptions import ErrorUpdateObject
from .meta_base import (
    BaseUpdater,
)
from examples.api_for_sqlalchemy.models import Post


class ErrorUpdatePostObject(ErrorUpdateObject):
    """Exception class for user update helper."""

    def __init__(self, description, field: str = ""):
        """Initialize constructor for exception while updating object."""
        super().__init__(Post, description, field)


class UpdatePost(BaseUpdater):
    """Post update helper."""

    class Meta:
        """Type of model."""

        model = Post

    fields_to_update = (
        'title',
        'body',
    )

    @classmethod
    async def before_update(
        cls,
        obj: Post,
        new_data: Dict[str, Any],
        header: Union[HeadersQueryStringManager, None] = None,
    ) -> Post:

        for field in cls.fields_to_update:
            cls._update_field_if_present_and_new(obj, new_data, field)
        return obj
