from typing import Dict, Literal

import pytest
from fastapi import Body, Depends, FastAPI, HTTPException, status
from httpx import AsyncClient
from pydantic import BaseModel
from pytest_asyncio import fixture
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_jsonapi.misc.sqla.generics.base import DetailViewBaseGeneric, ListViewBaseGeneric
from fastapi_jsonapi.views.utils import (
    HTTPMethod,
    HTTPMethodConfig,
)
from tests.fixtures.app import build_app_custom
from tests.fixtures.views import ArbitraryModelBase, SessionDependency, common_handler
from tests.misc.utils import fake
from tests.models import User
from tests.schemas import (
    UserAttributesBaseSchema,
    UserSchema,
)

pytestmark = pytest.mark.asyncio


FIELD_CUSTOM_NAME = "custom_name"


class CustomNameAttributeModel(BaseModel):
    custom_name: str


class CustomNameAttributeJSONAPI(BaseModel):
    attributes: CustomNameAttributeModel


def get_custom_name_from_body(
    data: CustomNameAttributeJSONAPI = Body(),
) -> str:
    return data.attributes.custom_name


class ValidateCustomNameEquals:
    STATUS_ON_ERROR = status.HTTP_400_BAD_REQUEST

    def __init__(self, expected_value):
        self.expected_value = expected_value

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
    method_dependencies: Dict[HTTPMethod, HTTPMethodConfig] = {
        HTTPMethod.ALL: HTTPMethodConfig(
            dependencies=SessionDependency,
            prepare_data_layer_kwargs=common_handler,
        ),
        HTTPMethod.POST: HTTPMethodConfig(
            dependencies=UserCreateCustomDependency,
        ),
    }


class UserCustomDetailView(DetailViewBaseGeneric):
    method_dependencies: Dict[HTTPMethod, HTTPMethodConfig] = {
        HTTPMethod.ALL: HTTPMethodConfig(
            dependencies=SessionDependency,
            prepare_data_layer_kwargs=common_handler,
        ),
        HTTPMethod.PATCH: HTTPMethodConfig(
            dependencies=UserUpdateCustomDependency,
        ),
    }


class TestCurrentAtomicOperation:
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

    def validate_field_not_passed_response(self, response):
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, response.text
        response_data = response.json()
        assert response_data == {
            "detail": [
                {
                    "loc": ["body", "data", "attributes", FIELD_CUSTOM_NAME],
                    "msg": "field required",
                    "type": "value_error.missing",
                },
            ],
        }

    def validate_field_value_invalid_response(self, response, expected_value):
        assert response.status_code == ValidateCustomNameEquals.STATUS_ON_ERROR, response.text
        response_data = response.json()
        assert response_data["detail"].pop("error")
        assert response_data == {
            "detail": {
                "expected_value": expected_value,
            },
        }

    async def test_generic_create_validation_error_key_not_passed(
        self,
        app_w_deps: FastAPI,
        client: AsyncClient,
        resource_type: str,
        user_attributes: UserAttributesBaseSchema,
    ):
        attributes_data = user_attributes.dict()
        data_user_create = {
            "data": {
                "type": resource_type,
                "attributes": attributes_data,
            },
        }
        url = app_w_deps.url_path_for(f"create_{resource_type}_list")
        response = await client.post(url, json=data_user_create)
        self.validate_field_not_passed_response(response)

    async def test_generic_update_validation_error_key_not_passed(
        self,
        app_w_deps: FastAPI,
        client: AsyncClient,
        resource_type: str,
        user_attributes: UserAttributesBaseSchema,
        user_1: User,
    ):
        attributes_data = user_attributes.dict()
        data_user_update = {
            "data": {
                "id": user_1.id,
                "type": resource_type,
                "attributes": attributes_data,
            },
        }
        url = app_w_deps.url_path_for(f"update_{resource_type}_detail", obj_id=user_1.id)
        response = await client.patch(url, json=data_user_update)
        self.validate_field_not_passed_response(response)

    async def test_generic_create_validation_error_value_passed_but_invalid(
        self,
        app_w_deps: FastAPI,
        client: AsyncClient,
        resource_type: str,
        user_attributes: UserAttributesBaseSchema,
    ):
        attributes_data = user_attributes.dict()
        attributes_data[FIELD_CUSTOM_NAME] = fake.word()
        data_user_create = {
            "data": {
                "type": resource_type,
                "attributes": attributes_data,
            },
        }
        url = app_w_deps.url_path_for(f"create_{resource_type}_list")
        response = await client.post(url, json=data_user_create)
        self.validate_field_value_invalid_response(response, validator_create.expected_value)

    async def test_generic_update_validation_error_value_passed_but_invalid(
        self,
        app_w_deps: FastAPI,
        client: AsyncClient,
        resource_type: str,
        user_attributes: UserAttributesBaseSchema,
        user_1: User,
    ):
        attributes_data = user_attributes.dict()
        attributes_data[FIELD_CUSTOM_NAME] = fake.word()
        data_user_create = {
            "data": {
                "type": resource_type,
                "attributes": attributes_data,
            },
        }
        url = app_w_deps.url_path_for(f"update_{resource_type}_detail", obj_id=user_1.id)
        response = await client.patch(url, json=data_user_create)
        self.validate_field_value_invalid_response(response, validator_update.expected_value)

    async def test_generic_create_works(
        self,
        app_w_deps: FastAPI,
        client: AsyncClient,
        async_session: AsyncSession,
        resource_type: str,
        user_attributes: UserAttributesBaseSchema,
    ):
        data_user_attributes = user_attributes.dict()
        data_user_attributes[FIELD_CUSTOM_NAME] = validator_create.expected_value
        data_user_create = {
            "data": {
                "type": resource_type,
                "attributes": data_user_attributes,
            },
        }
        url = app_w_deps.url_path_for(f"create_{resource_type}_list")
        response = await client.post(url, json=data_user_create)
        assert response.status_code == status.HTTP_201_CREATED, response.text
        user = await async_session.scalar(
            select(User).where(
                *(
                    # all filters
                    getattr(User, key) == value
                    # iterate obj by key + value
                    for key, value in user_attributes
                ),
            ),
        )
        assert isinstance(user, User)
        response_data = response.json()
        user_created_data = response_data["data"]
        assert user_created_data["id"] == str(user.id)
        assert user_created_data["attributes"] == user_attributes.dict()

    async def test_generic_update_works(
        self,
        app_w_deps: FastAPI,
        client: AsyncClient,
        async_session: AsyncSession,
        resource_type: str,
        user_attributes: UserAttributesBaseSchema,
        user_1: User,
    ):
        for field_name, value in user_attributes:
            assert getattr(user_1, field_name) != value

        data_user_attributes = user_attributes.dict()
        data_user_attributes[FIELD_CUSTOM_NAME] = validator_update.expected_value
        data_user_update = {
            "data": {
                "id": user_1.id,
                "type": resource_type,
                "attributes": data_user_attributes,
            },
        }
        url = app_w_deps.url_path_for(f"update_{resource_type}_detail", obj_id=user_1.id)
        response = await client.patch(url, json=data_user_update)
        assert response.status_code == status.HTTP_200_OK, response.text
        await async_session.refresh(user_1)
        response_data = response.json()
        user_created_data = response_data["data"]
        assert user_created_data["id"] == str(user_1.id)
        assert user_created_data["attributes"] == user_attributes.dict()
