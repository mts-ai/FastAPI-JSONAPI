from __future__ import annotations

from copy import deepcopy
from typing import (
    TYPE_CHECKING,
    Annotated,
    NoReturn,
    Callable,
)

import pytest
from fastapi import FastAPI, status
from httpx import AsyncClient
from pydantic import (
    BaseModel as PydanticBaseModel,
    ConfigDict,
    field_validator,
    model_validator,
    BeforeValidator,
    AfterValidator,
)
from pydantic_core.core_schema import ValidationInfo
from pytest_asyncio import fixture

from fastapi_jsonapi import RoutersJSONAPI
from fastapi_jsonapi.schema import BaseModel
from fastapi_jsonapi.schema_builder import SchemaBuilder
from fastapi_jsonapi.types_metadata import ClientCanSetId
from fastapi_jsonapi.validation_utils import extract_validators
from fastapi_jsonapi.views.view_base import ViewBase
from tests.fixtures.app import build_app_custom
from tests.misc.utils import fake
from tests.models import (
    Task,
    User,
)
from tests.schemas import TaskBaseSchema, UserAttributesBaseSchema

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


@fixture()
def refresh_caches() -> None:
    object_schemas_cache = deepcopy(SchemaBuilder.object_schemas_cache)
    relationship_schema_cache = deepcopy(SchemaBuilder.relationship_schema_cache)
    base_jsonapi_object_schemas_cache = deepcopy(SchemaBuilder.base_jsonapi_object_schemas_cache)

    all_jsonapi_routers = deepcopy(RoutersJSONAPI.all_jsonapi_routers)

    yield

    SchemaBuilder.object_schemas_cache = object_schemas_cache
    SchemaBuilder.relationship_schema_cache = relationship_schema_cache
    SchemaBuilder.base_jsonapi_object_schemas_cache = base_jsonapi_object_schemas_cache

    RoutersJSONAPI.all_jsonapi_routers = all_jsonapi_routers


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


@pytest.fixture()
def format_error() -> Callable[[str], str]:
    unique_marker = fake.word()

    def _format_error(v) -> str:
        return f"[{unique_marker}] Check validator for {v}"

    return _format_error


@pytest.fixture()
def reformat_error(format_error) -> Callable[[str, str], str]:
    def _reformat_error(marker, v) -> str:
        return f"[{marker}] {format_error(v)}"

    return _reformat_error


@pytest.mark.usefixtures("refresh_db", "refresh_caches")
class TestAnnotatedBeforeAndAfterValidators:

    @pytest.mark.parametrize("validator", [BeforeValidator, AfterValidator])
    async def test_validator_annotated(
        self,
        async_session: AsyncSession,
        validator: type[BeforeValidator] | type[AfterValidator],
    ) -> None:

        def mod_name(v: str) -> str:
            return v.title()

        def mod_age(v: int) -> int:
            return v * 2

        class UserAnnotatedFieldsSchema(UserAttributesBaseSchema):
            name: Annotated[str, validator(mod_name)]
            age: Annotated[int, validator(mod_age)]

        r_type = fake.word() + fake.word()
        app = build_app_custom(
            model=User,
            schema=UserAnnotatedFieldsSchema,
            resource_type=r_type,
        )

        raw_name = fake.name().lower()
        # raw_age = fake.pyint(min_value=13, max_value=99)
        raw_age = 80

        user_attrs = {
            "name": raw_name,
            "age": raw_age,
        }
        create_user_body = {
            "data": {
                "attributes": user_attrs,
            },
        }

        async with AsyncClient(app=app, base_url="http://test") as client:
            url = app.url_path_for(f"create_{r_type}_list")
            res = await client.post(url, json=create_user_body)
            assert res.status_code == status.HTTP_201_CREATED, res.text
            response_json = res.json()

        assert "data" in response_json
        data = response_json["data"]
        obj_id = data["id"]
        obj = await async_session.get(User, int(obj_id))

        assert data["type"] == r_type
        attributes = data["attributes"]
        user_name = attributes["name"]
        assert user_name != raw_name, attributes
        assert user_name == mod_name(raw_name), attributes
        user_age = attributes["age"]
        assert user_age != raw_age, attributes
        expected_age_in_db_after_deserialize = mod_age(raw_age)
        meta = {
            "raw age": raw_age,
            "user age": obj.age,
            "user id": obj.id,
            "user name": obj.name,
        }
        assert obj.age == expected_age_in_db_after_deserialize, meta
        expected_age_after_preparing_result = mod_age(expected_age_in_db_after_deserialize)
        assert user_age == expected_age_after_preparing_result, (attributes, meta)

    @pytest.mark.parametrize("validator", [BeforeValidator, AfterValidator])
    async def test_id_validator_annotated(
        self,
        validator: type[BeforeValidator] | type[AfterValidator],
        format_error,
    ):

        def validate_id_raise(v: str) -> NoReturn:
            raise ValueError(format_error(v))

        class UserAnnotatedIdValidatorSchema(UserAttributesBaseSchema):
            id: Annotated[int, ClientCanSetId(), validator(validate_id_raise)]

        r_type = fake.word() + fake.word()
        app = build_app_custom(
            model=User,
            schema=UserAnnotatedIdValidatorSchema,
            resource_type=r_type,
        )

        user_attrs = {
            "name": fake.name(),
        }
        new_user_id = fake.pyint(min_value=1000, max_value=10_000)
        create_user_body = {
            "data": {
                "attributes": user_attrs,
                "id": str(new_user_id),
            },
        }

        async with AsyncClient(app=app, base_url="http://test") as client:
            url = app.url_path_for(f"create_{r_type}_list")
            res = await client.post(url, json=create_user_body)
            assert res.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, res.text
            response_json = res.json()

        assert "detail" in response_json, response_json
        detail = response_json["detail"][0]
        assert detail["loc"] == ["body", "data", "id"]
        assert detail["msg"].endswith(format_error(new_user_id)), detail["msg"]

    @pytest.mark.parametrize("validator", [BeforeValidator, AfterValidator])
    async def test_validator_annotated_sequence_arg(
        self,
        validator: type[BeforeValidator] | type[AfterValidator],
        format_error,
    ):

        flag_name = fake.name()

        def validate_name(v):
            for item in v:
                if item == flag_name:
                    raise ValueError(format_error(item))

        class UserAnnotatedSequenceNamesSchema(UserAttributesBaseSchema):
            names: Annotated[list[str], validator(validate_name)]

        r_type = fake.word() + fake.word()
        app = build_app_custom(
            model=User,
            schema=UserAnnotatedSequenceNamesSchema,
            resource_type=r_type,
        )

        user_attrs = {
            "names": [fake.name(), flag_name],
            "name": fake.name(),
        }
        create_user_body = {
            "data": {
                "attributes": user_attrs,
            },
        }

        async with AsyncClient(app=app, base_url="http://test") as client:
            url = app.url_path_for(f"create_{r_type}_list")
            res = await client.post(url, json=create_user_body)
            assert res.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, res.text
            response_json = res.json()

        assert "detail" in response_json, response_json
        detail = response_json["detail"][0]
        assert detail["loc"] == ["body", "data", "attributes", "names"]
        assert detail["msg"].endswith(format_error(flag_name)), detail["msg"]


@pytest.mark.usefixtures("refresh_db")
class TestTaskValidators:
    async def test_base_model_validator_pre_true_get_one(
        self,
        app: FastAPI,
        client: AsyncClient,
        resource_type: str,
        task_with_none_ids: Task,
    ):
        assert task_with_none_ids.task_ids is None
        assert task_with_none_ids.another_task_ids is None
        url = app.url_path_for(f"get_{resource_type}_detail", obj_id=task_with_none_ids.id)
        res = await client.get(url)
        assert res.status_code == status.HTTP_200_OK, res.text
        response_data = res.json()
        attributes = response_data["data"].pop("attributes")
        assert response_data == {
            "data": {
                "id": ViewBase.get_db_item_id(task_with_none_ids),
                "type": resource_type,
                # dont' pass fields at all
            },
            "jsonapi": {"version": "1.0"},
            "meta": None,
        }
        assert attributes == {
            # not `None`! schema validator returns empty list `[]`
            "task_ids": [],
            "another_task_ids": [],
        }
        assert attributes == TaskBaseSchema.model_validate(task_with_none_ids).model_dump()

    async def test_base_model_model_validator_get_list(
        self,
        app: FastAPI,
        client: AsyncClient,
        resource_type: str,
        task_with_none_ids: Task,
    ):
        assert task_with_none_ids.task_ids is None
        assert task_with_none_ids.another_task_ids is None
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
                    "another_task_ids": [],
                },
            },
        ]
        assert response_data["data"] == expected_data

    async def test_base_model_model_validator_create(
        self,
        app: FastAPI,
        client: AsyncClient,
        resource_type: str,
        async_session: AsyncSession,
    ):
        task_data = {
            # should be converted to [] by schema on create
            "task_ids": None,
            "another_task_ids": None,
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
        assert task.another_task_ids == []
        assert response_data == {
            "data": {
                "type": resource_type,
                "attributes": {
                    # should be empty list
                    "task_ids": [],
                    "another_task_ids": [],
                },
            },
            "jsonapi": {"version": "1.0"},
            "meta": None,
        }


@pytest.mark.usefixtures("refresh_db", "refresh_caches")
class TestValidators:
    resource_type = "validator"

    def build_app(self, schema, resource_type: str | None = None) -> FastAPI:
        return build_app_custom(
            model=User,
            schema=schema,
            resource_type=resource_type or self.resource_type,
        )

    def inherit(self, schema: type[PydanticBaseModel]) -> type[PydanticBaseModel]:
        class InheritedSchema(schema):
            pass

        return InheritedSchema

    async def execute_request_and_check_response(
        self,
        app: FastAPI,
        body: dict,
        expected_detail: str,
        resource_type: str | None = None,
        expected_status: int = status.HTTP_422_UNPROCESSABLE_ENTITY,
    ):
        resource_type = resource_type or self.resource_type
        async with AsyncClient(app=app, base_url="http://test") as client:
            url = app.url_path_for(f"create_{resource_type}_list")
            res = await client.post(url, json=body)
            assert res.status_code == expected_status, res.text
            response_json = res.json()

        assert response_json
        assert "detail" in response_json, response_json
        error = response_json["detail"][0]
        assert error["msg"].endswith(expected_detail), (error, expected_detail)

    async def execute_request_twice_and_check_response(
        self,
        schema: type[PydanticBaseModel],
        body: dict,
        expected_detail: str,
        expected_status: int = status.HTTP_422_UNPROCESSABLE_ENTITY,
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
                expected_status=expected_status,
            )

    async def test_field_validator_call(self, format_error):
        """
        Basic check to ensure that field validator called
        """

        class UserSchemaWithValidator(PydanticBaseModel):
            name: str

            @field_validator("name")
            @staticmethod
            def validate_name(value):
                raise ValueError(format_error(value))

            model_config = ConfigDict(from_attributes=True)

        new_name = fake.name()
        attrs = {"name": new_name}
        create_user_body = {"data": {"attributes": attrs}}

        await self.execute_request_twice_and_check_response(
            schema=UserSchemaWithValidator,
            body=create_user_body,
            expected_detail=format_error(new_name),
        )

    async def test_field_validator_each_item_arg(self, format_error):
        flag_name = fake.word()

        class UserSchemaWithValidator(PydanticBaseModel):
            names: list[str]

            @field_validator("names")
            @staticmethod
            def validate_name(v):
                for item in v:
                    if item == flag_name:
                        raise ValueError(format_error(item))

            model_config = ConfigDict(from_attributes=True)

        attrs = {"names": [fake.name(), flag_name]}
        create_user_body = {"data": {"attributes": attrs}}

        await self.execute_request_twice_and_check_response(
            schema=UserSchemaWithValidator,
            body=create_user_body,
            expected_detail=format_error(flag_name),
        )

    async def test_field_validator_pre_arg(self, format_error):
        class UserSchemaWithValidator(PydanticBaseModel):
            name: list[str]

            @field_validator("name", mode="before")
            @staticmethod
            def validate_name_pre(value):
                raise ValueError(format_error(value))

            @field_validator("name", mode="after")
            @staticmethod
            def validate_name(value):
                raise ValueError("not this!")

            model_config = ConfigDict(from_attributes=True)

        new_name = fake.name()
        attrs = {"name": new_name}
        create_user_body = {"data": {"attributes": attrs}}

        await self.execute_request_twice_and_check_response(
            schema=UserSchemaWithValidator,
            body=create_user_body,
            expected_detail=format_error(new_name),
        )

    async def test_field_validator_always_arg(self, format_error):
        class UserSchemaWithValidator(PydanticBaseModel):
            name: str = None

            @field_validator("name")
            @staticmethod
            def validate_name(v):
                raise ValueError(format_error(v))

            model_config = ConfigDict(from_attributes=True)

        new_name = fake.name()
        create_user_body = {"data": {"attributes": {"name": new_name}}}

        await self.execute_request_twice_and_check_response(
            schema=UserSchemaWithValidator,
            body=create_user_body,
            expected_detail=format_error(new_name),
        )

    async def test_field_validator_several_validators(self, reformat_error):

        validator_1_marker = fake.word()
        validator_2_marker = fake.word()

        validator_1_flag = fake.sentence()
        validator_2_flag = fake.sentence()

        class UserSchemaWithValidator(PydanticBaseModel):
            field: str

            @field_validator("field")
            @staticmethod
            def validator_1(value):
                if value == validator_1_flag:
                    raise ValueError(reformat_error(validator_1_marker, value))

                return value

            @field_validator("field")
            @staticmethod
            def validator_2(value):
                if value == validator_2_flag:
                    raise ValueError(reformat_error(validator_2_marker, value))

                return value

            model_config = ConfigDict(from_attributes=True)

        attrs = {"field": validator_1_flag}
        create_user_body = {"data": {"attributes": attrs}}

        app = self.build_app(UserSchemaWithValidator)
        await self.execute_request_and_check_response(
            app=app,
            body=create_user_body,
            expected_detail=reformat_error(validator_1_marker, validator_1_flag),
        )

        attrs = {"field": validator_2_flag}
        create_user_body = {"data": {"attributes": attrs}}

        await self.execute_request_and_check_response(
            app=app,
            body=create_user_body,
            expected_detail=reformat_error(validator_2_marker, validator_2_flag),
        )

    async def test_field_validator_asterisk(self, reformat_error):
        bad_value = fake.word()

        class UserSchemaWithValidator(PydanticBaseModel):
            field_1: str
            field_2: str

            @field_validator("*", mode="before")
            @staticmethod
            def validator(v, validation_info: ValidationInfo):
                if v == bad_value:
                    raise ValueError(reformat_error(validation_info.field_name, v))
                return v

            model_config = ConfigDict(from_attributes=True)

        error_field = "field_1"
        attrs = {
            error_field: bad_value,
            "field_2": "",
        }
        create_user_body = {"data": {"attributes": attrs}}

        app = self.build_app(UserSchemaWithValidator)
        await self.execute_request_and_check_response(
            app=app,
            body=create_user_body,
            expected_detail=reformat_error(error_field, bad_value),
        )

        error_field = "field_2"
        attrs = {
            "field_1": "",
            error_field: bad_value,
        }
        create_user_body = {"data": {"attributes": attrs}}

        await self.execute_request_and_check_response(
            app=app,
            body=create_user_body,
            expected_detail=reformat_error(error_field, bad_value),
        )

    @pytest.mark.usefixtures("refresh_db")
    async def test_check_validator_for_id_field(self, format_error):
        """
        Unusual case because of "id" field handling in a different way than attributes
        """

        class UserSchemaWithValidator(PydanticBaseModel):
            id: Annotated[int, ClientCanSetId()]

            @field_validator("id", mode="after")
            @staticmethod
            def validate_id(value):
                raise ValueError(format_error(value))

            model_config = ConfigDict(from_attributes=True)

        id_val = fake.pyint(min_value=10, max_value=100)
        create_user_body = {
            "data": {
                "attributes": {"name": fake.name()},
                "id": str(id_val),
            },
        }

        await self.execute_request_twice_and_check_response(
            schema=UserSchemaWithValidator,
            body=create_user_body,
            expected_detail=format_error(id_val),
        )

    @pytest.mark.parametrize(
        "inherit",
        [
            pytest.param(True, id="inherited_true"),
            pytest.param(False, id="inherited_false"),
        ],
    )
    async def test_field_validator_can_change_value(self, inherit: bool):

        def modificator(v: str) -> str:
            return v.title()

        class UserSchemaWithValidator(PydanticBaseModel):
            name: str

            @field_validator("name")
            @staticmethod
            def fix_title(v):
                return modificator(v)

            model_config = ConfigDict(from_attributes=True)

        name_lower = fake.name().lower()
        attrs = {"name": name_lower}
        create_user_body = {"data": {"attributes": attrs}}

        if inherit:
            UserSchemaWithValidator = self.inherit(UserSchemaWithValidator)
        app = self.build_app(UserSchemaWithValidator)

        async with AsyncClient(app=app, base_url="http://test") as client:
            url = app.url_path_for(f"get_{self.resource_type}_list")
            res = await client.post(url, json=create_user_body)
            assert res.status_code == status.HTTP_201_CREATED, res.text

            res_json = res.json()

        expected_name = modificator(name_lower)
        assert expected_name != name_lower
        assert res_json["data"]
        assert res_json["data"]["id"]
        data = res_json["data"]
        data.pop("id")
        assert data == {
            "attributes": {"name": expected_name},
            "type": "validator",
        }

    @pytest.mark.parametrize(
        ("name_idx"),
        [
            pytest.param(0, id="check_1_pre_validator"),
            pytest.param(1, id="check_2_pre_validator"),
            pytest.param(2, id="check_1_post_validator"),
            pytest.param(3, id="check_2_post_validator"),
        ],
    )
    async def test_model_validators(self, reformat_error, name_idx: int):
        flag_pre_1 = fake.word() + "_pre_1"
        flag_pre_2 = fake.word() + "_pre_2"
        flag_post_1 = fake.word() + "_post_1"
        flag_post_2 = fake.word() + "_post_2"

        flags = [flag_pre_1, flag_pre_2, flag_post_1, flag_post_2]
        name = flags[name_idx]

        marker_pre_1 = fake.word() + "_pre_1"
        marker_pre_2 = fake.word() + "_pre_2"
        marker_post_1 = fake.word() + "_post_1"
        marker_post_2 = fake.word() + "_post_2"

        markers = [marker_pre_1, marker_pre_2, marker_post_1, marker_post_2]
        marker = markers[name_idx]

        class UserSchemaWithModelValidator(PydanticBaseModel):
            name: str

            @model_validator(mode="before")
            @staticmethod
            def validator_pre_1(values):
                if values["name"] == flag_pre_1:
                    raise ValueError(reformat_error(marker_pre_1, values["name"]))

                return values

            @model_validator(mode="before")
            @staticmethod
            def validator_pre_2(values):
                if values["name"] == flag_pre_2:
                    raise ValueError(reformat_error(marker_pre_2, values["name"]))

                return values

            @model_validator(mode="after")
            @staticmethod
            def validator_post_1(model):
                value_name = model.name
                if value_name == flag_post_1:
                    raise ValueError(reformat_error(marker_post_1, value_name))

                return model

            @model_validator(mode="after")
            @staticmethod
            def validator_post_2(model):
                value_name = model.name
                if value_name == flag_post_2:
                    raise ValueError(reformat_error(marker_post_2, value_name))

                return model

            model_config = ConfigDict(from_attributes=True)

        attrs = {"name": name}
        create_user_body = {"data": {"attributes": attrs}}

        await self.execute_request_twice_and_check_response(
            schema=UserSchemaWithModelValidator,
            body=create_user_body,
            expected_detail=reformat_error(marker, name),
        )

    @pytest.mark.parametrize(
        "inherit",
        [
            pytest.param(True, id="inherited_true"),
            pytest.param(False, id="inherited_false"),
        ],
    )
    async def test_model_validator_can_change_value(self, inherit: bool, format_error):

        def modificator(v: str) -> str:
            return v.title()

        class UserSchemaWithValidator(PydanticBaseModel):
            name: str

            @model_validator(mode="after")
            @staticmethod
            def fix_title(model):
                model.name = modificator(model.name)
                return model

            model_config = ConfigDict(from_attributes=True)

        new_name_lower = fake.name().lower()
        attrs = {"name": new_name_lower}
        create_user_body = {"data": {"attributes": attrs}}

        if inherit:
            UserSchemaWithValidator = self.inherit(UserSchemaWithValidator)
        app = self.build_app(UserSchemaWithValidator)

        async with AsyncClient(app=app, base_url="http://test") as client:
            url = app.url_path_for(f"get_{self.resource_type}_list")
            res = await client.post(url, json=create_user_body)
            assert res.status_code == status.HTTP_201_CREATED, res.text
            res_json = res.json()

        expected_name = modificator(new_name_lower)
        assert expected_name != new_name_lower

        assert res_json["data"]
        assert res_json["data"].pop("id")
        assert res_json == {
            "data": {
                "attributes": {"name": expected_name},
                "type": "validator",
            },
            "jsonapi": {"version": "1.0"},
            "meta": None,
        }

    @pytest.mark.parametrize(
        ("name_idx",),
        [
            pytest.param(0, id="check_1_pre_validator"),
            pytest.param(1, id="check_2_pre_validator"),
            pytest.param(2, id="check_1_post_validator"),
            pytest.param(3, id="check_2_post_validator"),
        ],
    )
    async def test_model_validator_inheritance(self, name_idx: int, reformat_error):
        flag_pre_1 = fake.word() + "_pre_1"
        flag_pre_2 = fake.word() + "_pre_2"
        flag_post_1 = fake.word() + "_post_1"
        flag_post_2 = fake.word() + "_post_2"

        flags = [flag_pre_1, flag_pre_2, flag_post_1, flag_post_2]
        name = flags[name_idx]

        marker_pre_1 = fake.word() + "_pre_1"
        marker_pre_2 = fake.word() + "_pre_2"
        marker_post_1 = fake.word() + "_post_1"
        marker_post_2 = fake.word() + "_post_2"

        markers = [marker_pre_1, marker_pre_2, marker_post_1, marker_post_2]
        marker = markers[name_idx]

        class UserSchemaWithValidatorBase(PydanticBaseModel):
            name: str

            @model_validator(mode="before")
            @staticmethod
            def validator_pre_1(values):
                if values["name"] == flag_pre_1:
                    raise ValueError(reformat_error(fake.word(), values["name"]))

                return values

            @model_validator(mode="before")
            @staticmethod
            def validator_pre_2(values):
                if values["name"] == flag_pre_2:
                    raise ValueError(reformat_error(fake.word(), values["name"]))

                return values

            @model_validator(mode="after")
            @staticmethod
            def validator_post_1(model):
                if model.name == flag_post_1:
                    raise ValueError(reformat_error(fake.word(), model.name))

                return model

            @model_validator(mode="after")
            @staticmethod
            def validator_post_2(model):
                if model.name == flag_post_2:
                    raise ValueError(reformat_error(fake.word(), model.name))

                return model

            model_config = ConfigDict(from_attributes=True)

        class UserSchemaWithValidator(UserSchemaWithValidatorBase):
            name: str

            @model_validator(mode="before")
            @staticmethod
            def validator_pre_1(values):
                if values["name"] == flag_pre_1:
                    raise ValueError(reformat_error(marker_pre_1, values["name"]))

                return values

            @model_validator(mode="before")
            @staticmethod
            def validator_pre_2(values):
                if values["name"] == flag_pre_2:
                    raise ValueError(reformat_error(marker_pre_2, values["name"]))

                return values

            @model_validator(mode="after")
            @staticmethod
            def validator_post_1(model):
                if model.name == flag_post_1:
                    raise ValueError(reformat_error(marker_post_1, model.name))

                return model

            @model_validator(mode="after")
            @staticmethod
            def validator_post_2(model):
                if model.name == flag_post_2:
                    raise ValueError(reformat_error(marker_post_2, model.name))

                return model

            model_config = ConfigDict(from_attributes=True)

        attrs = {"name": name}
        create_user_body = {"data": {"attributes": attrs}}

        await self.execute_request_and_check_response(
            app=self.build_app(UserSchemaWithValidator),
            body=create_user_body,
            expected_detail=reformat_error(marker, name),
        )


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

        validators = extract_validators(
            model=ValidationSchema,
            include_for_field_names=include,
            exclude_for_field_names=exclude,
        )

        assert set(validators) == expected
