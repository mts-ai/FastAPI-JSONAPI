from typing import (
    Any,
    Dict,
    Union,
)

from examples.api_for_tortoise_orm.models.enums import UserStatusEnum

from .exceptions import ErrorCreateObject
from .faker import fake
from .meta_base import (
    BaseFactory,
    FactoryUseMode,
)
from fastapi_jsonapi.querystring import HeadersQueryStringManager
from ...models.tortoise import User


class ErrorCreateUserObject(ErrorCreateObject):
    def __init__(self, description, field: str = ""):
        """Initialize constructor for exception while creating object."""
        super().__init__(User, description, field)


class UserFactory(BaseFactory):
    class Meta(object):
        model = User

    data = {
        "first_name": lambda: fake.word(),
        "last_name": lambda: fake.word(),
        "status": lambda: UserStatusEnum.active,
    }

    @classmethod
    async def before_create(
        cls,
        many: bool,
        mode: FactoryUseMode,
        model_kwargs: Dict,
        header: Union[HeadersQueryStringManager, None] = None,
    ) -> Dict:
        data_for_create_user: Dict[str, Any] = dict()
        cls._set_first_name(data_for_create_user, model_kwargs)
        cls._set_last_name(data_for_create_user, model_kwargs)
        cls._set_status(data_for_create_user, model_kwargs)
        return data_for_create_user

    @classmethod
    def _set_first_name(cls, data_for_create_user: Dict, kwargs: Dict):
        """
        Set first name.
        """
        data_for_create_user["first_name"] = kwargs.get("first_name", "First name")

    @classmethod
    def _set_last_name(cls, data_for_create_user: Dict, kwargs: Dict):
        """
        Set first name.
        """
        data_for_create_user["last_name"] = kwargs.get("last_name", "Last name")

    @classmethod
    def _set_status(cls, data_for_create_user: Dict, kwargs: Dict):
        """Status setter."""
        data_for_create_user["status"] = UserStatusEnum.active
