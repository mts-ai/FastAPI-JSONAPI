from typing import Literal

from fastapi import FastAPI
from httpx import AsyncClient
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from fastapi_jsonapi.views.view_base import ViewBase
from tests.misc.utils import fake
from tests.models import User
from tests.schemas import UserAttributesBaseSchema

FIELD_CUSTOM_NAME = "custom_name"


class CustomNameAttributeModel(BaseModel):
    custom_name: str


class CustomNameAttributesJSONAPI(BaseModel):
    attributes: CustomNameAttributeModel


class ValidateCustomNameEqualsBase:
    STATUS_ON_ERROR = status.HTTP_400_BAD_REQUEST

    def __init__(self, expected_value):
        self.expected_value = expected_value

    async def validate(self, custom_name: str) -> Literal[True]:
        raise NotImplementedError


class BaseGenericUserCreateUpdateWithBodyDependency:
    FIELD_CUSTOM_NAME = FIELD_CUSTOM_NAME
    validator_create = ValidateCustomNameEqualsBase(None)
    validator_update = ValidateCustomNameEqualsBase(None)

    def prepare_user_create_data(
        self,
        user_attributes: UserAttributesBaseSchema,
        resource_type: str,
    ):
        data_user_attributes = user_attributes.model_dump()
        data_user_attributes[self.FIELD_CUSTOM_NAME] = self.validator_create.expected_value
        return {
            "type": resource_type,
            "attributes": data_user_attributes,
        }

    def prepare_user_update_data(
        self,
        user: User,
        user_attributes: UserAttributesBaseSchema,
        resource_type: str,
    ):
        for field_name, value in user_attributes:
            assert getattr(user, field_name) != value

        data_user_attributes = user_attributes.model_dump()
        data_user_attributes[self.FIELD_CUSTOM_NAME] = self.validator_update.expected_value
        return {
            "id": ViewBase.get_db_item_id(user),
            "type": resource_type,
            "attributes": data_user_attributes,
        }

    def validate_field_not_passed_response(
        self,
        response,
        input_data: dict,
        expected_status=status.HTTP_422_UNPROCESSABLE_ENTITY,
    ):
        assert response.status_code == expected_status, response.text
        response_data = response.json()
        assert len(response_data["detail"]) == 1
        detail = response_data["detail"][0]
        detail.pop("url", None)
        assert detail == {
            "input": input_data,
            "loc": ["body", "data", "attributes", self.FIELD_CUSTOM_NAME],
            "msg": "Field required",
            "type": "missing",
        }

    def validate_field_value_invalid_response(self, response, validator: ValidateCustomNameEqualsBase):
        assert response.status_code == validator.STATUS_ON_ERROR, response.text
        response_data = response.json()
        assert response_data["detail"].pop("error")
        assert response_data == {
            "detail": {
                "expected_value": validator.expected_value,
            },
        }

    async def validate_user_creation_on_error_key_not_passed(
        self,
        app: FastAPI,
        client: AsyncClient,
        resource_type: str,
        user_attributes: UserAttributesBaseSchema,
    ):
        attributes_data = user_attributes.model_dump()
        assert self.FIELD_CUSTOM_NAME not in attributes_data
        data_user_create = {
            "data": {
                "type": resource_type,
                "attributes": attributes_data,
            },
        }
        url = app.url_path_for(f"create_{resource_type}_list")
        response = await client.post(url, json=data_user_create)
        self.validate_field_not_passed_response(
            response,
            input_data=attributes_data,
        )

    async def validate_user_creation_test_error_value_passed_but_invalid(
        self,
        app: FastAPI,
        client: AsyncClient,
        resource_type: str,
        user_attributes: UserAttributesBaseSchema,
    ):
        attributes_data = user_attributes.model_dump()
        attributes_data[self.FIELD_CUSTOM_NAME] = fake.word()
        assert attributes_data[self.FIELD_CUSTOM_NAME] != self.validator_create.expected_value
        data_user_create = {
            "data": {
                "type": resource_type,
                "attributes": attributes_data,
            },
        }
        url = app.url_path_for(f"create_{resource_type}_list")
        response = await client.post(url, json=data_user_create)
        self.validate_field_value_invalid_response(response, self.validator_create)

    async def validate_user_update_error_key_not_passed(
        self,
        app: FastAPI,
        client: AsyncClient,
        user: User,
        resource_type: str,
        user_attributes: UserAttributesBaseSchema,
    ):
        attributes_data = user_attributes.model_dump()
        assert self.FIELD_CUSTOM_NAME not in attributes_data
        data_user_update = {
            "data": {
                "id": ViewBase.get_db_item_id(user),
                "type": resource_type,
                "attributes": attributes_data,
            },
        }
        url = app.url_path_for(f"update_{resource_type}_detail", obj_id=user.id)
        response = await client.patch(url, json=data_user_update)
        self.validate_field_not_passed_response(
            response,
            input_data=attributes_data,
        )

    async def validate_user_update_error_value_passed_but_invalid(
        self,
        app: FastAPI,
        client: AsyncClient,
        user: User,
        resource_type: str,
        user_attributes: UserAttributesBaseSchema,
    ):
        attributes_data = user_attributes.model_dump()
        attributes_data[self.FIELD_CUSTOM_NAME] = fake.word()
        assert attributes_data[self.FIELD_CUSTOM_NAME] != self.validator_update.expected_value
        data_user_update = {
            "data": {
                "id": ViewBase.get_db_item_id(user),
                "type": resource_type,
                "attributes": attributes_data,
            },
        }
        url = app.url_path_for(f"update_{resource_type}_detail", obj_id=user.id)
        response = await client.patch(url, json=data_user_update)
        self.validate_field_value_invalid_response(response, self.validator_update)

    async def validate_created_user(
        self,
        async_session: AsyncSession,
        user_created_data: dict,
        user_attributes: UserAttributesBaseSchema,
        resource_type: str,
    ):
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
        assert user_created_data["id"] == str(user.id)
        assert user_created_data["attributes"] == user_attributes.model_dump()
        assert user_created_data["type"] == resource_type
        assert user_attributes == UserAttributesBaseSchema.model_validate(user)

    async def validate_generic_user_create_works(
        self,
        app: FastAPI,
        client: AsyncClient,
        async_session: AsyncSession,
        resource_type: str,
        user_attributes: UserAttributesBaseSchema,
    ):
        data_user_create = self.prepare_user_create_data(
            user_attributes=user_attributes,
            resource_type=resource_type,
        )
        url = app.url_path_for(f"create_{resource_type}_list")
        response = await client.post(url, json={"data": data_user_create})
        assert response.status_code == status.HTTP_201_CREATED, response.text
        response_data = response.json()
        user_created_data = response_data["data"]
        await self.validate_created_user(
            async_session=async_session,
            user_created_data=user_created_data,
            user_attributes=user_attributes,
            resource_type=resource_type,
        )

    async def validate_updated_user(
        self,
        user: User,
        async_session: AsyncSession,
        user_updated_data: dict,
        user_attributes: UserAttributesBaseSchema,
        resource_type: str,
    ):
        await async_session.refresh(user)
        assert user_updated_data["id"] == str(user.id)
        assert user_updated_data["attributes"] == user_attributes.model_dump()
        assert user_updated_data["type"] == resource_type
        assert user_attributes == UserAttributesBaseSchema.model_validate(user)

    async def validate_generic_user_update_works(
        self,
        app: FastAPI,
        client: AsyncClient,
        async_session: AsyncSession,
        resource_type: str,
        user_attributes: UserAttributesBaseSchema,
        user: User,
    ):
        data_user_update = self.prepare_user_update_data(
            user=user,
            user_attributes=user_attributes,
            resource_type=resource_type,
        )
        url = app.url_path_for(f"update_{resource_type}_detail", obj_id=user.id)
        response = await client.patch(url, json={"data": data_user_update})
        assert response.status_code == status.HTTP_200_OK, response.text
        response_data = response.json()
        user_updated_data = response_data["data"]
        await self.validate_updated_user(
            user=user,
            async_session=async_session,
            user_updated_data=user_updated_data,
            user_attributes=user_attributes,
            resource_type=resource_type,
        )
