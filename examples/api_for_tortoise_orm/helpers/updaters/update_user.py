"""Update user helper."""

from typing import (
    Any,
    Dict,
    Optional,
    Union,
)

from fastapi_jsonapi.querystring import HeadersQueryStringManager
from .exceptions import ErrorUpdateObject
from .meta_base import (
    BaseUpdater,
)
from ...models.enums import UserStatusEnum
from ...models.tortoise import User


class ErrorUpdateUserObject(ErrorUpdateObject):
    """Exception class for user update helper."""

    def __init__(self, description, field: str = ""):
        """Initialize constructor for exception while updating object."""
        super().__init__(User, description, field)


class UpdateUser(BaseUpdater):
    """User update helper."""

    class Meta(object):
        """Type of model."""

        model = User

    @classmethod
    async def before_update(
        cls,
        obj: User,
        new_data: Dict[str, Any],
        header: Union[HeadersQueryStringManager, None] = None,
    ) -> User:
        cls._update_first_name(obj, new_data)
        cls._update_last_name(obj, new_data)
        cls._update_status(obj, new_data)
        return obj

    @classmethod
    def _update_first_name(cls, obj: User, new_data: Dict[str, Any]) -> None:
        first_name: Optional[str] = new_data.get("first_name")
        if first_name is not None and first_name != obj.first_name:
            obj.first_name = first_name

    @classmethod
    def _update_last_name(cls, obj: User, new_data: Dict[str, Any]) -> None:
        last_name: Optional[str] = new_data.get("last_name")
        if last_name is not None and last_name != obj.last_name:
            obj.last_name = last_name

    @classmethod
    def _update_status(
        cls,
        obj: User,
        new_data: Dict[str, Any],
    ) -> None:
        new_status: Optional[UserStatusEnum] = new_data.get("status")
        if new_status is None or new_status == obj.status:
            return None

        if new_status is User.Enum.status.block and obj.status is not User.Enum.status.active:
            obj.status = new_status
