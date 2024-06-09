from __future__ import annotations

from copy import deepcopy
from typing import (
    TYPE_CHECKING,
    Annotated,
)

import pytest
from fastapi import FastAPI, status
from httpx import AsyncClient
from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from pytest_asyncio import fixture

from fastapi_jsonapi import RoutersJSONAPI
from fastapi_jsonapi.exceptions import BadRequest
from fastapi_jsonapi.schema_builder import SchemaBuilder
from fastapi_jsonapi.types_metadata import ClientCanSetId
from fastapi_jsonapi.validation_utils import extract_field_validators
from fastapi_jsonapi.views.view_base import ViewBase
from tests.fixtures.app import build_app_custom
from tests.misc.utils import fake
from tests.models import (
    Task,
    User,
)
from tests.schemas import TaskBaseSchema

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


# TODO: Support Annotated validators (Before/After)


@fixture()
async def task_with_none_ids(
    async_session: AsyncSession,
) -> Task:
    task = Task(task_ids=None)
    async_session.add(task)
    await async_session.commit()

    return task


@pytest.fixture()
def resource_type():
    return "task"


@pytest.mark.xfail(reason="validators passthrough not supported yet")
class TestTaskValidators:
    async def test_base_model_validator_pre_true_get_one(
        self,
        app: FastAPI,
        client: AsyncClient,
        resource_type: str,
        task_with_none_ids: Task,
    ):
        assert task_with_none_ids.task_ids is None
        url = app.url_path_for(f"get_{resource_type}_detail", obj_id=task_with_none_ids.id)
        res = await client.get(url)
        assert res.status_code == status.HTTP_200_OK, res.text
        response_data = res.json()
        attributes = response_data["data"].pop("attributes")
        assert response_data == {
            "data": {
                "id": ViewBase.get_db_item_id(task_with_none_ids),
                "type": resource_type,
            },
            "jsonapi": {"version": "1.0"},
            "meta": None,
        }
        assert attributes == {
            # not `None`! schema validator returns empty list `[]`
            "task_ids": [],
        }
        assert attributes == TaskBaseSchema.model_validate(task_with_none_ids)

    async def test_base_model_root_validator_get_list(
        self,
        app: FastAPI,
        client: AsyncClient,
        resource_type: str,
        task_with_none_ids: Task,
    ):
        assert task_with_none_ids.task_ids is None
        url = app.url_path_for(f"get_{resource_type}_list")
        res = await client.get(url)
        assert res.status_code == status.HTTP_200_OK, res.text
        response_data = res.json()
        expected_data = [
            {
                "id": ViewBase.get_db_item_id(task_with_none_ids),
                "type": resource_type,
                "attributes": {
                    # not `None`! schema validator returns empty list `[]`
                    "task_ids": [],
                },
            },
        ]
        assert response_data["data"] == expected_data

    async def test_base_model_root_validator_create(
        self,
        app: FastAPI,
        client: AsyncClient,
        resource_type: str,
        async_session: AsyncSession,
    ):
        task_data = {
            # should be converted to [] by schema on create
            "task_ids": None,
        }
        data_create = {
            "data": {
                "type": resource_type,
                "attributes": task_data,
            },
        }
        url = app.url_path_for(f"create_{resource_type}_list")
        res = await client.post(url, json=data_create)
        assert res.status_code == status.HTTP_201_CREATED, res.text
        response_data: dict = res.json()
        task_id = response_data["data"].pop("id")
        task = await async_session.get(Task, int(task_id))
        assert isinstance(task, Task)
        # we sent request with `None`, but value in db is `[]`
        # because validator converted data before object creation
        assert task.task_ids == []
        assert response_data == {
            "data": {
                "type": resource_type,
                "attributes": {
                    # should be empty list
                    "task_ids": [],
                },
            },
            "jsonapi": {"version": "1.0"},
            "meta": None,
        }


@pytest.mark.xfail(reason="validators passthrough not supported yet")
class TestValidators:
    resource_type = "validator"

    @fixture(autouse=True)
    def _refresh_caches(self) -> None:
        object_schemas_cache = deepcopy(SchemaBuilder.object_schemas_cache)
        relationship_schema_cache = deepcopy(SchemaBuilder.relationship_schema_cache)
        base_jsonapi_object_schemas_cache = deepcopy(SchemaBuilder.base_jsonapi_object_schemas_cache)

        all_jsonapi_routers = deepcopy(RoutersJSONAPI.all_jsonapi_routers)

        yield

        SchemaBuilder.object_schemas_cache = object_schemas_cache
        SchemaBuilder.relationship_schema_cache = relationship_schema_cache
        SchemaBuilder.base_jsonapi_object_schemas_cache = base_jsonapi_object_schemas_cache

        RoutersJSONAPI.all_jsonapi_routers = all_jsonapi_routers

    def build_app(self, schema, resource_type: str | None = None) -> FastAPI:
        return build_app_custom(
            model=User,
            schema=schema,
            resource_type=resource_type or self.resource_type,
        )

    def inherit(self, schema: type[BaseModel]) -> type[BaseModel]:
        class InheritedSchema(schema):
            pass

        return InheritedSchema

    async def execute_request_and_check_response(
        self,
        app: FastAPI,
        body: dict,
        expected_detail: str,
        resource_type: str | None = None,
    ):
        resource_type = resource_type or self.resource_type
        async with AsyncClient(app=app, base_url="http://test") as client:
            url = app.url_path_for(f"get_{resource_type}_list")
            res = await client.post(url, json=body)
            assert res.status_code == status.HTTP_400_BAD_REQUEST, res.text
            assert res.json() == {
                "errors": [
                    {
                        "detail": expected_detail,
                        "source": {"pointer": ""},
                        "status_code": status.HTTP_400_BAD_REQUEST,
                        "title": "Bad Request",
                    },
                ],
            }

    async def execute_request_twice_and_check_response(
        self,
        schema: type[BaseModel],
        body: dict,
        expected_detail: str,
    ):
        """
        Makes two requests for check schema inheritance
        """
        resource_type_1 = self.resource_type + fake.word()
        app_1 = self.build_app(schema, resource_type=resource_type_1)
        resource_type_2 = self.resource_type + fake.word()
        app_2 = self.build_app(self.inherit(schema), resource_type=resource_type_2)

        for app, resource_type in [(app_1, resource_type_1), (app_2, resource_type_2)]:
            await self.execute_request_and_check_response(
                app=app,
                body=body,
                expected_detail=expected_detail,
                resource_type=resource_type,
            )

    async def test_field_validator_call(self):
        """
        Basic check to ensure that field validator called
        """

        class UserSchemaWithValidator(BaseModel):
            name: str

            @field_validator("name")
            @classmethod
            def validate_name(cls, v):
                # checks that cls arg is not bound to the origin class
                assert cls is not UserSchemaWithValidator

                raise BadRequest(detail=f"Check validator for {v}")

            model_config = ConfigDict(from_attributes=True)

        attrs = {"name": fake.name()}
        create_user_body = {"data": {"attributes": attrs}}

        await self.execute_request_twice_and_check_response(
            schema=UserSchemaWithValidator,
            body=create_user_body,
            expected_detail="Check validator",
        )

    async def test_field_validator_each_item_arg(self):
        class UserSchemaWithValidator(BaseModel):
            names: list[str]

            @field_validator("names")
            @classmethod
            def validate_name(cls, v):
                for item in v:
                    if item == "bad_name":
                        raise BadRequest(detail="Bad name not allowed")

            model_config = ConfigDict(from_attributes=True)

        attrs = {"names": ["good_name", "bad_name"]}
        create_user_body = {"data": {"attributes": attrs}}

        await self.execute_request_twice_and_check_response(
            schema=UserSchemaWithValidator,
            body=create_user_body,
            expected_detail="Bad name not allowed",
        )

    async def test_field_validator_pre_arg(self):
        class UserSchemaWithValidator(BaseModel):
            name: list[str]

            @field_validator("name", mode="before")
            @classmethod
            def validate_name_pre(cls, v):
                raise BadRequest(detail=f"Pre validator called for {v}")

            @field_validator("name")
            @classmethod
            def validate_name(cls, v):
                raise BadRequest(detail=f"Not pre validator called for {v}")

            model_config = ConfigDict(from_attributes=True)

        attrs = {"name": fake.name()}
        create_user_body = {"data": {"attributes": attrs}}

        await self.execute_request_twice_and_check_response(
            schema=UserSchemaWithValidator,
            body=create_user_body,
            expected_detail="Pre validator called",
        )

    async def test_field_validator_always_arg(self):
        class UserSchemaWithValidator(BaseModel):
            name: str = None

            @field_validator("name")
            @classmethod
            def validate_name(cls, v):
                raise BadRequest(detail=f"Called always validator for {v}")

            model_config = ConfigDict(from_attributes=True)

        create_user_body = {"data": {"attributes": {}}}

        await self.execute_request_twice_and_check_response(
            schema=UserSchemaWithValidator,
            body=create_user_body,
            expected_detail="Called always validator",
        )

    async def test_field_validator_several_validators(self):
        class UserSchemaWithValidator(BaseModel):
            field: str

            @field_validator("field")
            @classmethod
            def validator_1(cls, v):
                if v == "check_validator_1":
                    raise BadRequest(detail="Called validator 1")

                return v

            @field_validator("field")
            @classmethod
            def validator_2(cls, v):
                if v == "check_validator_2":
                    raise BadRequest(detail="Called validator 2")

                return v

            model_config = ConfigDict(from_attributes=True)

        attrs = {"field": "check_validator_1"}
        create_user_body = {"data": {"attributes": attrs}}

        app = self.build_app(UserSchemaWithValidator)
        await self.execute_request_and_check_response(
            app=app,
            body=create_user_body,
            expected_detail="Called validator 1",
        )

        attrs = {"field": "check_validator_2"}
        create_user_body = {"data": {"attributes": attrs}}

        await self.execute_request_and_check_response(
            app=app,
            body=create_user_body,
            expected_detail="Called validator 2",
        )

    async def test_field_validator_asterisk(self):
        class UserSchemaWithValidator(BaseModel):
            field_1: str
            field_2: str

            @field_validator("*", mode="before")
            @classmethod
            def validator(cls, v):
                if v == "bad_value":
                    raise BadRequest(detail="Check validator")

            model_config = ConfigDict(from_attributes=True)

        attrs = {
            "field_1": "bad_value",
            "field_2": "",
        }
        create_user_body = {"data": {"attributes": attrs}}

        app = self.build_app(UserSchemaWithValidator)
        await self.execute_request_and_check_response(
            app=app,
            body=create_user_body,
            expected_detail="Check validator",
        )

        attrs = {
            "field_1": "",
            "field_2": "bad_value",
        }
        create_user_body = {"data": {"attributes": attrs}}

        await self.execute_request_and_check_response(
            app=app,
            body=create_user_body,
            expected_detail="Check validator",
        )

    async def test_check_validator_for_id_field(self):
        """
        Unusual case because of "id" field handling in a different way than attributes
        """

        class UserSchemaWithValidator(BaseModel):
            id: Annotated[int, ClientCanSetId()]

            @field_validator("id")
            @classmethod
            def validate_id(cls, v):
                raise BadRequest(detail=f"Check validator for {v}")

            model_config = ConfigDict(from_attributes=True)

        create_user_body = {
            "data": {
                "attributes": {},
                "id": str(42),
            },
        }

        await self.execute_request_twice_and_check_response(
            schema=UserSchemaWithValidator,
            body=create_user_body,
            expected_detail="Check validator",
        )

    @pytest.mark.parametrize(
        "inherit",
        [
            pytest.param(True, id="inherited_true"),
            pytest.param(False, id="inherited_false"),
        ],
    )
    async def test_field_validator_can_change_value(self, inherit: bool):
        class UserSchemaWithValidator(BaseModel):
            name: str

            @field_validator("name")
            @classmethod
            def fix_title(cls, v):
                return v.title()

            model_config = ConfigDict(from_attributes=True)

        attrs = {"name": "john doe"}
        create_user_body = {"data": {"attributes": attrs}}

        if inherit:
            UserSchemaWithValidator = self.inherit(UserSchemaWithValidator)
        app = self.build_app(UserSchemaWithValidator)

        async with AsyncClient(app=app, base_url="http://test") as client:
            url = app.url_path_for(f"get_{self.resource_type}_list")
            res = await client.post(url, json=create_user_body)
            assert res.status_code == status.HTTP_201_CREATED, res.text

            res_json = res.json()
            assert res_json["data"]
            assert res_json["data"].pop("id")
            assert res_json == {
                "data": {
                    "attributes": {"name": "John Doe"},
                    "type": "validator",
                },
                "jsonapi": {"version": "1.0"},
                "meta": None,
            }

    @pytest.mark.parametrize(
        ("name", "expected_detail"),
        [
            pytest.param("check_pre_1", "Raised 1 pre validator", id="check_1_pre_validator"),
            pytest.param("check_pre_2", "Raised 2 pre validator", id="check_2_pre_validator"),
            pytest.param("check_post_1", "Raised 1 post validator", id="check_1_post_validator"),
            pytest.param("check_post_2", "Raised 2 post validator", id="check_2_post_validator"),
        ],
    )
    async def test_root_validator(self, name: str, expected_detail: str):
        class UserSchemaWithValidator(BaseModel):
            name: str

            @model_validator(mode="before")
            @classmethod
            def validator_pre_1(cls, values):
                if values["name"] == "check_pre_1":
                    raise BadRequest(detail="Raised 1 pre validator")

                return values

            @model_validator(mode="before")
            @classmethod
            def validator_pre_2(cls, values):
                if values["name"] == "check_pre_2":
                    raise BadRequest(detail="Raised 2 pre validator")

                return values

            @model_validator(mode="after")
            @classmethod
            def validator_post_1(cls, values):
                if values["name"] == "check_post_1":
                    raise BadRequest(detail="Raised 1 post validator")

                return values

            @model_validator(mode="after")
            @classmethod
            def validator_post_2(cls, values):
                if values["name"] == "check_post_2":
                    raise BadRequest(detail="Raised 2 post validator")

                return values

            model_config = ConfigDict(from_attributes=True)

        attrs = {"name": name}
        create_user_body = {"data": {"attributes": attrs}}

        await self.execute_request_twice_and_check_response(
            schema=UserSchemaWithValidator,
            body=create_user_body,
            expected_detail=expected_detail,
        )

    @pytest.mark.parametrize(
        "inherit",
        [
            pytest.param(True, id="inherited_true"),
            pytest.param(False, id="inherited_false"),
        ],
    )
    async def test_root_validator_can_change_value(self, inherit: bool):
        class UserSchemaWithValidator(BaseModel):
            name: str

            @model_validator(mode="after")
            @classmethod
            def fix_title(cls, v):
                v["name"] = v["name"].title()
                return v

            model_config = ConfigDict(from_attributes=True)

        attrs = {"name": "john doe"}
        create_user_body = {"data": {"attributes": attrs}}

        if inherit:
            UserSchemaWithValidator = self.inherit(UserSchemaWithValidator)
        app = self.build_app(UserSchemaWithValidator)

        async with AsyncClient(app=app, base_url="http://test") as client:
            url = app.url_path_for(f"get_{self.resource_type}_list")
            res = await client.post(url, json=create_user_body)
            assert res.status_code == status.HTTP_201_CREATED, res.text

            res_json = res.json()
            assert res_json["data"]
            assert res_json["data"].pop("id")
            assert res_json == {
                "data": {
                    "attributes": {"name": "John Doe"},
                    "type": "validator",
                },
                "jsonapi": {"version": "1.0"},
                "meta": None,
            }

    @pytest.mark.parametrize(
        ("name", "expected_detail"),
        [
            pytest.param("check_pre_1", "check_pre_1", id="check_1_pre_validator"),
            pytest.param("check_pre_2", "check_pre_2", id="check_2_pre_validator"),
            pytest.param("check_post_1", "check_post_1", id="check_1_post_validator"),
            pytest.param("check_post_2", "check_post_2", id="check_2_post_validator"),
        ],
    )
    async def test_root_validator_inheritance(self, name: str, expected_detail: str):
        class UserSchemaWithValidatorBase(BaseModel):
            name: str

            @model_validator(mode="before")
            @classmethod
            def validator_pre_1(cls, values):
                if values["name"] == "check_pre_1":
                    raise BadRequest(detail="Base check_pre_1")

                return values

            @model_validator(mode="before")
            @classmethod
            def validator_pre_2(cls, values):
                if values["name"] == "check_pre_2":
                    raise BadRequest(detail="Base check_pre_2")

                return values

            @classmethod
            def validator_post_1(cls, values):
                if values["name"] == "check_post_1":
                    raise BadRequest(detail="Base check_post_1")

                return values

            @classmethod
            def validator_post_2(cls, values):
                if values["name"] == "check_post_2":
                    raise BadRequest(detail="Base check_post_2")

                return values

            model_config = ConfigDict(from_attributes=True)

        class UserSchemaWithValidator(UserSchemaWithValidatorBase):
            name: str

            @model_validator(mode="before")
            @classmethod
            def validator_pre_1(cls, values):
                if values["name"] == "check_pre_1":
                    raise BadRequest(detail="check_pre_1")

                return values

            @model_validator(mode="before")
            @classmethod
            def validator_pre_2(cls, values):
                if values["name"] == "check_pre_2":
                    raise BadRequest(detail="check_pre_2")

                return values

            @classmethod
            def validator_post_1(cls, values):
                if values["name"] == "check_post_1":
                    raise BadRequest(detail="check_post_1")

                return values

            @classmethod
            def validator_post_2(cls, values):
                if values["name"] == "check_post_2":
                    raise BadRequest(detail="check_post_2")

                return values

            model_config = ConfigDict(from_attributes=True)

        attrs = {"name": name}
        create_user_body = {"data": {"attributes": attrs}}

        await self.execute_request_and_check_response(
            app=self.build_app(UserSchemaWithValidator),
            body=create_user_body,
            expected_detail=expected_detail,
        )


@pytest.mark.xfail(reason="validators passthrough not supported yet")
class TestValidationUtils:
    @pytest.mark.parametrize(
        ("include", "exclude", "expected"),
        [
            pytest.param({"item_1"}, None, {"item_1_validator"}, id="include"),
            pytest.param(None, {"item_1"}, {"item_2_validator"}, id="exclude"),
            pytest.param(None, None, {"item_1_validator", "item_2_validator"}, id="empty_params"),
            pytest.param({"item_1", "item_2"}, {"item_2"}, {"item_1_validator"}, id="intersection"),
        ],
    )
    def test_extract_field_validators_args(
        self,
        exclude: set[str],
        include: set[str],
        expected: set[str],
    ):
        class ValidationSchema(BaseModel):
            item_1: str
            item_2: str

            @field_validator("item_1")
            @classmethod
            def item_1_validator(cls, v):
                return v

            @field_validator("item_2")
            @classmethod
            def item_2_validator(cls, v):
                return v

        validators = extract_field_validators(
            model=ValidationSchema,
            include_for_field_names=include,
            exclude_for_field_names=exclude,
        )
        validator_func_names = {
            validator_item.__validator_config__[1].func.__name__ for validator_item in validators.values()
        }

        assert expected == validator_func_names
