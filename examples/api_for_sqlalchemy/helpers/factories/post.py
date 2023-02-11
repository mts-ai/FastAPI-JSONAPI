from typing import (
    Any,
    Dict,
    Union,
)

from .exceptions import ErrorCreateObject
from .faker import fake
from .meta_base import (
    BaseFactory,
    FactoryUseMode,
)
from fastapi_rest_jsonapi.querystring import HeadersQueryStringManager
from examples.api_for_sqlalchemy.models import User, Post


class ErrorCreatePostObject(ErrorCreateObject):
    def __init__(self, description, field: str = ""):
        """Initialize constructor for exception while creating object."""
        super().__init__(Post, description, field)


async def create_user(db_se) -> User:
    raise NotImplemented


class PostFactory(BaseFactory):
    class Meta:
        model = Post

    data = {
        "title": lambda: fake.sentence(),
        "body": lambda: fake.sentence(),
        "user": create_user,
    }

    set_field_on_create = (
        'title',
        'body',
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
