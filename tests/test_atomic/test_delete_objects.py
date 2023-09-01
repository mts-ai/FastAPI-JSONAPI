import logging
from typing import Awaitable, Callable

from httpx import AsyncClient
from pytest import mark  # noqa
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import count
from starlette import status

from tests.models import Computer
from tests.schemas import ComputerAttributesBaseSchema

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
                    "data": {
                        "id": str(computer_1.id),
                        "type": "computer",
                    },
                },
                {
                    "op": "remove",
                    "data": {
                        "id": str(computer_2.id),
                        "type": "computer",
                    },
                },
            ],
        }
        response = await client.post("/operations", json=data_atomic_request)
        assert response.status_code == status.HTTP_200_OK, response.text
        response_data = response.json()
        assert "atomic:results" in response_data, response_data
        results = response_data["atomic:results"]
        assert results

        computers_count = await async_session.scalar(stmt_computers)
        assert computers_count == 0

        assert results == [
            {
                "data": {
                    "id": str(computer_1.id),
                    "type": "computer",
                    "attributes": ComputerAttributesBaseSchema.from_orm(computer_1),
                },
                "meta": None,
            },
            {
                "data": {
                    "id": str(computer_2.id),
                    "type": "computer",
                    "attributes": ComputerAttributesBaseSchema.from_orm(computer_2),
                },
                "meta": None,
            },
        ]
