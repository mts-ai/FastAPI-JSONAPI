from typing import (
    Any,
    Dict,
    Union,
)

from examples.api_for_sqlalchemy.models import User, UserBio
from fastapi_jsonapi.misc.sqla.factories.exceptions import ErrorCreateObject
from fastapi_jsonapi.misc.sqla.factories.meta_base import (
    BaseFactory,
    FactoryUseMode,
)
from fastapi_jsonapi.querystring import HeadersQueryStringManager

from .faker import fake


class ErrorCreateUserBioObject(ErrorCreateObject):
    def __init__(self, description, field: str = ""):
        """Initialize constructor for exception while creating object."""
        super().__init__(UserBio, description, field)


async def create_user(db_se) -> User:
    raise NotImplementedError


class UserBioFactory(BaseFactory):
    class Meta:
        model = UserBio

    data = {
        "birth_city": lambda: fake.sentence(),
        "favourite_movies": lambda: fake.sentence(),
        "user": create_user,
        "keys_to_ids_list": lambda: {"key": [1, 2, 3]},
    }

    set_field_on_create = (
        "birth_city",
        "favourite_movies",
        "keys_to_ids_list",
        # "user_id",
    )

    @classmethod
    async def before_create(
        cls,
        many: bool,
        mode: FactoryUseMode,
        model_kwargs: Dict,
        header: Union[HeadersQueryStringManager, None] = None,
    ) -> Dict:
        data_for_create: Dict[str, Any] = {}
        for field_name in cls.set_field_on_create:
            await cls._prepare_attribute_or_raise(field_name, data_for_create, model_kwargs)

        return data_for_create
