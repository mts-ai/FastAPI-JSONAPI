from typing import ClassVar, Dict, Literal

import pytest
from fastapi import Body, Depends, FastAPI, HTTPException, status
from httpx import AsyncClient
from pytest_asyncio import fixture
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_jsonapi.misc.sqla.generics.base import DetailViewBaseGeneric, ListViewBaseGeneric
from fastapi_jsonapi.views.utils import (
    HTTPMethod,
    HTTPMethodConfig,
)
from tests.common_user_api_test import (
    BaseGenericUserCreateUpdateWithBodyDependency,
    CustomNameAttributesJSONAPI,
    ValidateCustomNameEqualsBase,
)
from tests.fixtures.app import build_app_custom
from tests.fixtures.views import ArbitraryModelBase, SessionDependency, common_handler
from tests.models import User
from tests.schemas import (
    UserAttributesBaseSchema,
    UserSchema,
)

pytestmark = pytest.mark.asyncio


def get_custom_name_from_body(
    data: CustomNameAttributesJSONAPI = Body(),
) -> str:
    return data.attributes.custom_name


class ValidateCustomNameEquals(ValidateCustomNameEqualsBase):
    STATUS_ON_ERROR = status.HTTP_400_BAD_REQUEST

    async def validate(
        self,
        custom_name: str = Depends(get_custom_name_from_body),
    ) -> Literal[True]:
        """
        Assert body.data.attributes[key] == value

        :return:
        """
        if custom_name == self.expected_value:
            return True

        raise HTTPException(
            detail={
                "error": f"expected value {self.expected_value!r}",
                "expected_value": self.expected_value,
            },
            status_code=self.STATUS_ON_ERROR,
        )


validator_create = ValidateCustomNameEquals("custom_value_on_create")


class UserCreateCustomDependency(ArbitraryModelBase):
    allow: bool = Depends(validator_create.validate)


validator_update = ValidateCustomNameEquals("custom_value_on_update")


class UserUpdateCustomDependency(ArbitraryModelBase):
    allow: bool = Depends(validator_update.validate)


class UserCustomListView(ListViewBaseGeneric):
    method_dependencies: ClassVar[Dict[HTTPMethod, HTTPMethodConfig]] = {
        HTTPMethod.ALL: HTTPMethodConfig(
            dependencies=SessionDependency,
            prepare_data_layer_kwargs=common_handler,
        ),
        HTTPMethod.POST: HTTPMethodConfig(
            dependencies=UserCreateCustomDependency,
        ),
    }


class UserCustomDetailView(DetailViewBaseGeneric):
    method_dependencies: ClassVar[Dict[HTTPMethod, HTTPMethodConfig]] = {
        HTTPMethod.ALL: HTTPMethodConfig(
            dependencies=SessionDependency,
            prepare_data_layer_kwargs=common_handler,
        ),
        HTTPMethod.PATCH: HTTPMethodConfig(
            dependencies=UserUpdateCustomDependency,
        ),
    }


class TestGenericUserCreateUpdateWithBodyDependency(
    BaseGenericUserCreateUpdateWithBodyDependency,
):
    validator_create = validator_create
    validator_update = validator_update

    @pytest.fixture(scope="class")
    def resource_type(self):
        return "user_w_custom_deps_for_generic"

    @pytest.fixture(scope="class")
    def app_w_deps(self, resource_type):
        app = build_app_custom(
            model=User,
            schema=UserSchema,
            resource_type=resource_type,
            class_list=UserCustomListView,
            class_detail=UserCustomDetailView,
            path=f"/path_{resource_type}",
        )
        return app

    @fixture(scope="class")
    async def client(self, app_w_deps: FastAPI):
        async with AsyncClient(app=app_w_deps, base_url="http://test") as client:
            yield client

    async def test_generic_create_validation_error_key_not_passed(
        self,
        app_w_deps: FastAPI,
        client: AsyncClient,
        resource_type: str,
        user_attributes: UserAttributesBaseSchema,
    ):
        await self.validate_user_creation_on_error_key_not_passed(
            app=app_w_deps,
            client=client,
            resource_type=resource_type,
            user_attributes=user_attributes,
        )

    async def test_generic_update_validation_error_key_not_passed(
        self,
        app_w_deps: FastAPI,
        client: AsyncClient,
        resource_type: str,
        user_attributes: UserAttributesBaseSchema,
        user_1: User,
    ):
        await self.validate_user_update_error_key_not_passed(
            app=app_w_deps,
            client=client,
            user=user_1,
            resource_type=resource_type,
            user_attributes=user_attributes,
        )

    async def test_generic_create_validation_error_value_passed_but_invalid(
        self,
        app_w_deps: FastAPI,
        client: AsyncClient,
        resource_type: str,
        user_attributes: UserAttributesBaseSchema,
    ):
        await self.validate_user_creation_test_error_value_passed_but_invalid(
            app=app_w_deps,
            client=client,
            resource_type=resource_type,
            user_attributes=user_attributes,
        )

    async def test_generic_update_validation_error_value_passed_but_invalid(
        self,
        app_w_deps: FastAPI,
        client: AsyncClient,
        resource_type: str,
        user_attributes: UserAttributesBaseSchema,
        user_1: User,
    ):
        await self.validate_user_update_error_value_passed_but_invalid(
            app=app_w_deps,
            client=client,
            user=user_1,
            resource_type=resource_type,
            user_attributes=user_attributes,
        )

    async def test_generic_create_works(
        self,
        app_w_deps: FastAPI,
        client: AsyncClient,
        async_session: AsyncSession,
        resource_type: str,
        user_attributes: UserAttributesBaseSchema,
    ):
        await self.validate_generic_user_create_works(
            app=app_w_deps,
            client=client,
            async_session=async_session,
            resource_type=resource_type,
            user_attributes=user_attributes,
        )

    async def test_generic_update_works(
        self,
        app_w_deps: FastAPI,
        client: AsyncClient,
        async_session: AsyncSession,
        resource_type: str,
        user_attributes: UserAttributesBaseSchema,
        user_1: User,
    ):
        await self.validate_generic_user_update_works(
            app=app_w_deps,
            client=client,
            async_session=async_session,
            resource_type=resource_type,
            user_attributes=user_attributes,
            user=user_1,
        )
