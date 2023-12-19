from typing import ClassVar, Dict

import pytest
from fastapi import Depends, Query, status
from httpx import AsyncClient
from pytest_asyncio import fixture

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
    UserInSchema,
    UserPatchSchema,
    UserSchema,
)

pytestmark = pytest.mark.asyncio


class CustomDependencyForCreate:
    KEY = "spam_create"

    def __init__(self, query_spam: str = Query(..., alias=KEY)):
        self.query_spam = query_spam


class CustomDependencyForUpdate:
    KEY = "spam_update"

    def __init__(self, query_spam: str = Query(..., alias=KEY)):
        self.query_spam = query_spam


class CustomDependencyForDelete:
    KEY = "spam_delete"

    def __init__(self, query_spam: str = Query(..., alias=KEY)):
        self.query_spam = query_spam


class UserCreateCustomDependency(ArbitraryModelBase):
    dep: CustomDependencyForCreate = Depends()


class UserUpdateCustomDependency(ArbitraryModelBase):
    dep: CustomDependencyForUpdate = Depends()


class UserDeleteCustomDependency(ArbitraryModelBase):
    dep: CustomDependencyForDelete = Depends()


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
        HTTPMethod.DELETE: HTTPMethodConfig(
            dependencies=UserDeleteCustomDependency,
        ),
    }


class TestDependenciesResolver:
    @pytest.fixture(scope="class")
    def resource_type(self):
        return "user_custom_deps"

    @pytest.fixture(scope="class")
    def app_w_deps(self, resource_type):
        app = build_app_custom(
            model=User,
            schema=UserSchema,
            schema_in_post=UserInSchema,
            schema_in_patch=UserPatchSchema,
            resource_type=resource_type,
            class_list=UserCustomListView,
            class_detail=UserCustomDetailView,
        )
        return app

    @fixture(scope="class")
    async def client(self, app_w_deps):
        async with AsyncClient(app=app_w_deps, base_url="http://test") as client:
            yield client

    async def send_and_validate_atomic(
        self,
        client: AsyncClient,
        data_atomic: dict,
        expected_body: dict,
        expected_status=status.HTTP_422_UNPROCESSABLE_ENTITY,
    ):
        response = await client.post("/operations", json=data_atomic)
        assert response.status_code == expected_status, response.text
        response_data = response.json()
        # TODO: JSON:API exception
        assert response_data == expected_body

    async def test_on_create_atomic(
        self,
        client: AsyncClient,
        resource_type: str,
    ):
        user = UserAttributesBaseSchema(
            name=fake.name(),
            age=fake.pyint(min_value=13, max_value=99),
            email=fake.email(),
        )
        data_atomic_request = {
            "atomic:operations": [
                {
                    "op": "add",
                    "data": {
                        "type": resource_type,
                        "attributes": user.dict(),
                    },
                },
            ],
        }
        # TODO: JSON:API exception
        expected_response_data = {
            "detail": [
                {
                    "loc": ["query", CustomDependencyForCreate.KEY],
                    "msg": "field required",
                    "type": "value_error.missing",
                },
            ],
        }
        await self.send_and_validate_atomic(
            client=client,
            data_atomic=data_atomic_request,
            expected_body=expected_response_data,
        )

    async def test_on_update_atomic(
        self,
        client: AsyncClient,
        resource_type: str,
        user_1: User,
    ):
        user = UserAttributesBaseSchema(
            name=fake.name(),
            age=fake.pyint(min_value=13, max_value=99),
            email=fake.email(),
        )
        data_atomic_request = {
            "atomic:operations": [
                {
                    "op": "update",
                    "id": user_1.id,
                    "data": {
                        "type": resource_type,
                        "attributes": user.dict(),
                    },
                },
            ],
        }  # TODO: JSON:API exception
        expected_response_data = {
            "detail": [
                {
                    "loc": ["query", CustomDependencyForUpdate.KEY],
                    "msg": "field required",
                    "type": "value_error.missing",
                },
            ],
        }
        await self.send_and_validate_atomic(
            client=client,
            data_atomic=data_atomic_request,
            expected_body=expected_response_data,
        )

    async def test_on_delete_atomic(
        self,
        client: AsyncClient,
        resource_type: str,
        user_1: User,
    ):
        data_atomic_request = {
            "atomic:operations": [
                {
                    "op": "remove",
                    "ref": {
                        "id": user_1.id,
                        "type": resource_type,
                    },
                },
            ],
        }
        # TODO: JSON:API exception
        expected_response_data = {
            "detail": [
                {
                    "loc": ["query", CustomDependencyForDelete.KEY],
                    "msg": "field required",
                    "type": "value_error.missing",
                },
            ],
        }
        await self.send_and_validate_atomic(
            client=client,
            data_atomic=data_atomic_request,
            expected_body=expected_response_data,
        )
