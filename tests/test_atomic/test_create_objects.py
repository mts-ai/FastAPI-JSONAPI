import logging

from httpx import AsyncClient
from pytest import mark  # noqa
from sqlalchemy import and_, or_, select
from sqlalchemy.engine import Result
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import count
from starlette import status

from tests.misc.utils import fake
from tests.models import User
from tests.schemas import UserAttributesBaseSchema

pytestmark = mark.asyncio

logging.basicConfig(level=logging.DEBUG)


class TestAtomicCreateObjects:
    async def test_operations_empty_list(self, client: AsyncClient):
        data_atomic_request = {
            "atomic:operations": [],
        }
        response = await client.post("/operations", json=data_atomic_request)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, response.text
        assert response.json() == {
            # TODO: JSON:API exception!
            "detail": [
                {
                    "loc": ["body", "atomic:operations"],
                    "msg": "ensure this value has at least 1 items",
                    "type": "value_error.list.min_items",
                    "ctx": {"limit_value": 1},
                },
            ],
        }

    async def test_create_one_object(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
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
                        "type": "user",
                        "attributes": user.dict(),
                    },
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
        stmt = select(User).where(
            User.name == user.name,
            User.age == user.age,
            User.email == user.email,
        )
        db_result: Result = await async_session.execute(stmt)
        user_obj: User = db_result.scalar_one()
        assert result.pop("meta") is None
        assert result == {
            "data": {
                "attributes": UserAttributesBaseSchema.from_orm(user_obj).dict(),
                "id": str(user_obj.id),
                "type": "user",
            },
        }

    async def test_create_two_objects(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
    ):
        user_data_1 = UserAttributesBaseSchema(
            name=fake.name(),
            age=fake.pyint(min_value=13, max_value=99),
            email=fake.email(),
        )
        user_data_2 = UserAttributesBaseSchema(
            name=fake.name(),
            age=fake.pyint(min_value=13, max_value=99),
            email=fake.email(),
        )
        users_data = [user_data_1, user_data_2]
        data_atomic_request = {
            "atomic:operations": [
                {
                    "op": "add",
                    "data": {
                        "type": "user",
                        "attributes": user_data.dict(),
                    },
                }
                for user_data in users_data
            ],
        }
        response = await client.post("/operations", json=data_atomic_request)
        assert response.status_code == status.HTTP_200_OK, response.text
        response_data = response.json()
        assert "atomic:results" in response_data, response_data
        results = response_data["atomic:results"]
        assert results, results
        stmt = select(User).where(
            or_(
                and_(
                    User.name == user_data.name,
                    User.age == user_data.age,
                    User.email == user_data.email,
                )
                for user_data in users_data
            ),
        )
        db_result: Result = await async_session.execute(stmt)
        users: list[User] = db_result.scalars().all()
        assert len(users) == len(results)
        for result, user in zip(results, users):
            assert result.pop("meta") is None
            assert result == {
                "data": {
                    "attributes": UserAttributesBaseSchema.from_orm(user).dict(),
                    "id": str(user.id),
                    "type": "user",
                },
            }

    async def test_atomic_rollback_on_create_error(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
    ):
        """
        User name is unique

        - create first user
        - create second user with the same name
        - catch exc
        - rollback all changes

        :param client:
        :param async_session:
        :return:
        """
        user_data_1 = UserAttributesBaseSchema(
            name=fake.name(),
            age=fake.pyint(min_value=13, max_value=99),
            email=fake.email(),
        )
        user_data_2 = UserAttributesBaseSchema(
            name=user_data_1.name,
            age=fake.pyint(min_value=13, max_value=99),
            email=fake.email(),
        )
        users_data = [user_data_1, user_data_2]
        data_atomic_request = {
            "atomic:operations": [
                {
                    "op": "add",
                    "data": {
                        "type": "user",
                        "attributes": user_data.dict(),
                    },
                }
                for user_data in users_data
            ],
        }
        response = await client.post("/operations", json=data_atomic_request)
        assert response.status_code == status.HTTP_400_BAD_REQUEST, response.text
        response_data = response.json()
        assert "errors" in response_data, response_data
        errors = response_data["errors"]
        assert errors, response_data
        error = errors[0]
        assert error == {
            "detail": "Object creation error",
            "source": {"pointer": "/data"},
            "status_code": status.HTTP_400_BAD_REQUEST,
            "title": "Bad Request",
        }
        stmt = select(count(User.id)).where(
            or_(
                User.name == user_data_1.name,
                User.name == user_data_2.name,
            ),
        )
        result: Result = await async_session.execute(stmt)
        assert result.scalar_one() == 0
