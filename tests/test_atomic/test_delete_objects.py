import logging
from typing import Awaitable, Callable

from httpx import AsyncClient
from pytest import mark  # noqa
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import count
from starlette import status

from fastapi_jsonapi.atomic.schemas import AtomicOperationAction
from tests.models import Computer

pytestmark = mark.asyncio

logging.basicConfig(level=logging.DEBUG)


class TestAtomicDeleteObjects:
    async def test_delete_two_objects(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        computer_factory: Callable[..., Awaitable[Computer]],
    ):
        computer_1 = await computer_factory()
        computer_2 = await computer_factory()

        computers_ids = [
            computer_1.id,
            computer_2.id,
        ]
        stmt_computers = select(count(Computer.id)).where(
            Computer.id.in_(computers_ids),
        )
        computers_count = await async_session.scalar(stmt_computers)
        assert computers_count == len(computers_ids)

        data_atomic_request = {
            "atomic:operations": [
                {
                    "op": "remove",
                    "ref": {
                        "id": str(computer_1.id),
                        "type": "computer",
                    },
                },
                {
                    "op": "remove",
                    "ref": {
                        "id": str(computer_2.id),
                        "type": "computer",
                    },
                },
            ],
        }
        response = await client.post("/operations", json=data_atomic_request)
        assert response.status_code == status.HTTP_204_NO_CONTENT, response.text
        assert response.content == b""

        computers_count = await async_session.scalar(stmt_computers)
        assert computers_count == 0

    async def test_delete_no_ref(
        self,
        client: AsyncClient,
    ):
        data_atomic_request = {
            "atomic:operations": [
                {
                    "op": "remove",
                    "data": {
                        "id": "0",
                        "type": "computer",
                    },
                },
            ],
        }
        response = await client.post("/operations", json=data_atomic_request)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, response.text
        assert response.json() == {
            # TODO: json:api exception
            "detail": [
                {
                    "loc": ["body", "atomic:operations", 0, "__root__"],
                    "msg": f"ref should be present for action {AtomicOperationAction.remove.value!r}",
                    "type": "value_error",
                },
            ],
        }
