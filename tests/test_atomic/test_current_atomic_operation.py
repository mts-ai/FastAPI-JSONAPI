from __future__ import annotations

from typing import Dict, Literal, Optional

import pytest
from fastapi import Body, Depends, FastAPI, HTTPException, status
from httpx import AsyncClient
from pydantic import BaseModel
from pytest_asyncio import fixture
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_jsonapi.atomic import current_atomic_operation
from fastapi_jsonapi.misc.sqla.generics.base import DetailViewBaseGeneric, ListViewBaseGeneric
from fastapi_jsonapi.utils.exceptions import handle_validation_error
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
from tests.misc.utils import fake
from tests.models import User
from tests.schemas import (
    UserAttributesBaseSchema,
    UserSchema,
)

pytestmark = pytest.mark.asyncio


FIELD_CUSTOM_NAME = "custom_name"


# this one can be used only for generic views
# def get_custom_name_from_body_only_on_generic(
#     data: CustomNameAttributesJSONAPI = Body(embed=True),
# ) -> str:
#     return data.attributes.custom_name


missing = object()


# XXX: These two models below only for a valid exception path location!
#  you don't really need to do it this way if you don't need valid error path `loc`


class AttributesData(BaseModel):
    data: CustomNameAttributesJSONAPI


class AttributesTopLevelBody(BaseModel):
    body: AttributesData


@handle_validation_error
def get_validated_attribute_from_body(data: dict):
    # # this will work ok, but `loc` in exception text will be `'loc': ['attributes', 'custom_name']`
    # # and we need `'loc': ['body', 'data', 'attributes', 'custom_name']`
    # validated_data = CustomNameAttributesJSONAPI.parse_obj(data)
    # return validated_data.attributes.custom_name

    validated_data = AttributesTopLevelBody.parse_obj({"body": {"data": data}})

    # or
    # return get_custom_name_from_body_only_on_generic(data=validated_data)
    # or
    return validated_data.body.data.attributes.custom_name


async def get_custom_name_from_body_universal(
    data: Optional[dict] = Body(None, embed=True),
) -> str:
    atomic_operation = current_atomic_operation.get(missing)
    if atomic_operation is missing:
        # example for same helper both for generic view and atomic view
        return get_validated_attribute_from_body(data)

        # # use dependencies helper because it will raise corresponding errors
        # dep_helper = DependencyHelper(request=request)
        # return await dep_helper.run(get_custom_name_from_body_only_on_generic)

    return get_validated_attribute_from_body(atomic_operation.data.dict())


class ValidateCustomNameEquals(ValidateCustomNameEqualsBase):
    STATUS_ON_ERROR = status.HTTP_400_BAD_REQUEST

    async def validate(
        self,
        custom_name: str = Depends(get_custom_name_from_body_universal),
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


validator_create = ValidateCustomNameEquals("custom_value_on_create_universal")


class UserCreateCustomDependency(ArbitraryModelBase):
    allow: bool = Depends(validator_create.validate)


validator_update = ValidateCustomNameEquals("custom_value_on_update_universal")


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


class TestSameBodyDependencyBothForGenericsAndCurrentAtomicOperation(
    BaseGenericUserCreateUpdateWithBodyDependency,
):
    validator_create = validator_create
    validator_update = validator_update

    @pytest.fixture(scope="class")
    def resource_type(self):
        return "user_w_custom_deps_for_body"

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

    async def test_atomic_create_user_error_required_body_field_not_passed(
        self,
        client: AsyncClient,
        resource_type: str,
        user_attributes: UserAttributesBaseSchema,
    ):
        user_attributes_data = user_attributes.dict()
        assert self.FIELD_CUSTOM_NAME not in user_attributes_data
        data_atomic_request = {
            "atomic:operations": [
                {
                    "op": "add",
                    "data": {
                        "type": resource_type,
                        "attributes": user_attributes_data,
                    },
                },
            ],
        }
        response = await client.post("/operations", json=data_atomic_request)
        self.validate_field_not_passed_response(response)

    async def test_atomic_update_user_error_required_body_field_not_passed(
        self,
        client: AsyncClient,
        resource_type: str,
        user_attributes: UserAttributesBaseSchema,
        user_1: User,
    ):
        attributes_data = user_attributes.dict()
        assert self.FIELD_CUSTOM_NAME not in attributes_data
        data_user_update = {
            "id": user_1.id,
            "type": resource_type,
            "attributes": attributes_data,
        }
        data_atomic_request = {
            "atomic:operations": [
                {
                    "op": "update",
                    "data": data_user_update,
                },
            ],
        }
        response = await client.post("/operations", json=data_atomic_request)
        self.validate_field_not_passed_response(response)

    async def test_atomic_create_user_error_required_body_field_passed_but_invalid(
        self,
        client: AsyncClient,
        resource_type: str,
        user_attributes: UserAttributesBaseSchema,
    ):
        user_attributes_data = user_attributes.dict()
        user_attributes_data[self.FIELD_CUSTOM_NAME] = fake.word()
        assert user_attributes_data[self.FIELD_CUSTOM_NAME] != self.validator_create.expected_value
        data_atomic_request = {
            "atomic:operations": [
                {
                    "op": "add",
                    "data": {
                        "type": resource_type,
                        "attributes": user_attributes_data,
                    },
                },
            ],
        }
        response = await client.post("/operations", json=data_atomic_request)
        self.validate_field_value_invalid_response(response, self.validator_create)

    async def test_atomic_update_user_error_required_body_field_passed_but_invalid(
        self,
        client: AsyncClient,
        resource_type: str,
        user_attributes: UserAttributesBaseSchema,
        user_1: User,
    ):
        attributes_data = user_attributes.dict()
        attributes_data[self.FIELD_CUSTOM_NAME] = fake.word()
        data_user_update = {
            "id": user_1.id,
            "type": resource_type,
            "attributes": attributes_data,
        }
        data_atomic_request = {
            "atomic:operations": [
                {
                    "op": "update",
                    "data": data_user_update,
                },
            ],
        }
        response = await client.post("/operations", json=data_atomic_request)
        self.validate_field_value_invalid_response(response, self.validator_update)

    async def test_atomic_create_user_success_use_current_atomic_operation_during_validation(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        resource_type: str,
        user_attributes: UserAttributesBaseSchema,
    ):
        data_user_create = self.prepare_user_create_data(
            user_attributes=user_attributes,
            resource_type=resource_type,
        )
        data_atomic_request = {
            "atomic:operations": [
                {
                    "op": "add",
                    "data": data_user_create,
                },
            ],
        }
        response = await client.post("/operations", json=data_atomic_request)
        assert response.status_code == status.HTTP_200_OK, response.text
        response_data = response.json()
        assert "atomic:results" in response_data, response_data
        results = response_data["atomic:results"]
        assert results, results
        result: dict = results[0]

        assert result.pop("meta") is None

        await self.validate_created_user(
            async_session=async_session,
            user_created_data=result["data"],
            user_attributes=user_attributes,
            resource_type=resource_type,
        )

    async def test_atomic_update_user_success_use_current_atomic_operation_during_validation(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        resource_type: str,
        user_attributes: UserAttributesBaseSchema,
        user_1: User,
    ):
        data_user_update = self.prepare_user_update_data(
            user=user_1,
            user_attributes=user_attributes,
            resource_type=resource_type,
        )
        data_atomic_request = {
            "atomic:operations": [
                {
                    "op": "update",
                    "data": data_user_update,
                },
            ],
        }
        response = await client.post("/operations", json=data_atomic_request)
        assert response.status_code == status.HTTP_200_OK, response.text
        response_data = response.json()
        assert "atomic:results" in response_data, response_data
        results = response_data["atomic:results"]
        assert results, results
        result: dict = results[0]

        assert result.pop("meta") is None

        await self.validate_updated_user(
            user=user_1,
            async_session=async_session,
            user_updated_data=result["data"],
            user_attributes=user_attributes,
            resource_type=resource_type,
        )
