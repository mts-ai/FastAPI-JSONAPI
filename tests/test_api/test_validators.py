import pytest
from fastapi import FastAPI, status
from httpx import AsyncClient
from pytest_asyncio import fixture
from sqlalchemy.ext.asyncio import AsyncSession

from tests.models import Task
from tests.schemas import TaskBaseSchema

pytestmark = pytest.mark.asyncio


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


class TestTaskValidators:
    async def test_base_model_root_validator_get_one(
        self,
        app: FastAPI,
        client: AsyncClient,
        resource_type: str,
        task_with_none_ids: Task,
    ):
        url = app.url_path_for(f"get_{resource_type}_detail", obj_id=task_with_none_ids.id)
        res = await client.get(url)
        assert res.status_code == status.HTTP_200_OK, res.text
        response_data = res.json()
        attributes = response_data["data"].pop("attributes")
        assert response_data == {
            "data": {
                "id": str(task_with_none_ids.id),
                "type": resource_type,
            },
            "jsonapi": {"version": "1.0"},
            "meta": None,
        }
        assert attributes == {
            # not `None`! schema validator returns empty list `[]`
            # "task_ids": None,
            "task_ids": [],
        }
        assert attributes == TaskBaseSchema.from_orm(task_with_none_ids)

    async def test_base_model_root_validator_get_list(
        self,
        app: FastAPI,
        client: AsyncClient,
        resource_type: str,
        task_with_none_ids: Task,
    ):
        url = app.url_path_for(f"get_{resource_type}_list")
        res = await client.get(url)
        assert res.status_code == status.HTTP_200_OK, res.text
        response_data = res.json()
        assert response_data == {
            "data": [
                {
                    "id": str(task_with_none_ids.id),
                    "type": resource_type,
                    "attributes": {
                        # not `None`! schema validator returns empty list `[]`
                        # "task_ids": None,
                        "task_ids": [],
                    },
                },
            ],
            "jsonapi": {
                "version": "1.0",
            },
            "meta": {
                "count": 1,
                "totalPages": 1,
            },
        }

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
