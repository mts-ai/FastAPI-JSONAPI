import logging

from httpx import AsyncClient
from pytest import mark  # noqa
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import count
from starlette import status

from tests.misc.utils import fake
from tests.models import Computer, User, UserBio
from tests.schemas import ComputerAttributesBaseSchema, UserAttributesBaseSchema, UserBioBaseSchema

pytestmark = mark.asyncio

logging.basicConfig(level=logging.DEBUG)


class TestAtomicMixedActions:
    async def test_schema_validation_error(
        self,
        client: AsyncClient,
        allowed_atomic_actions_list: list[str],
        allowed_atomic_actions_as_string: str,
    ):
        operation_name = fake.word()
        atomic_request_data = {
            "atomic:operations": [
                {
                    "op": operation_name,
                    "href": "/any",
                    "data": {
                        "type": "any",
                        "attributes": {
                            "any": "any",
                        },
                    },
                },
            ],
        }
        response = await client.post("/operations", json=atomic_request_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, response.text
        response_data = response.json()

        assert response_data == {
            # TODO: jsonapi exception?
            "detail": [
                {
                    "loc": ["body", "atomic:operations", 0, "op"],
                    "msg": f"value is not a valid enumeration member; permitted: {allowed_atomic_actions_as_string}",
                    "type": "type_error.enum",
                    "ctx": {
                        "enum_values": allowed_atomic_actions_list,
                    },
                },
            ],
        }

    async def test_create_and_update_atomic_success(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        user_1: User,
        user_1_bio: UserBio,
    ):
        """
        Create computer for user
        Update user's Bio
        Update user

        :param client:
        :param async_session:
        :param user_1:
        :param user_1_bio:
        :return:
        """
        user_data = UserAttributesBaseSchema.from_orm(user_1)
        user_bio_data = UserBioBaseSchema.from_orm(user_1_bio)
        user_data.name = fake.name()
        user_bio_data.favourite_movies = fake.sentence()
        assert user_1.name != user_data.name
        assert user_1_bio.favourite_movies != user_bio_data.favourite_movies
        new_computer = ComputerAttributesBaseSchema(
            name=fake.user_name(),
        )
        data_atomic_request = {
            "atomic:operations": [
                {
                    "op": "add",
                    "data": {
                        "type": "computer",
                        "attributes": new_computer.dict(),
                        "relationships": {
                            "user": {
                                "data": {
                                    "id": user_1.id,
                                    "type": "user",
                                },
                            },
                        },
                    },
                },
                {
                    "op": "update",
                    "data": {
                        "id": str(user_1_bio.id),
                        "type": "user_bio",
                        "attributes": user_bio_data.dict(),
                    },
                },
                {
                    "op": "update",
                    "data": {
                        "id": str(user_1.id),
                        "type": "user",
                        "attributes": user_data.dict(),
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
        await async_session.refresh(user_1)
        await async_session.refresh(user_1_bio)
        assert user_1.name == user_data.name
        assert user_1_bio.favourite_movies == user_bio_data.favourite_movies
        computer: Computer = await async_session.scalar(select(Computer).where(Computer.user_id == user_1.id))
        assert results == [
            {
                "data": {
                    "id": str(computer.id),
                    "type": "computer",
                    "attributes": new_computer.dict(),
                },
                "meta": None,
            },
            {
                "data": {
                    "id": str(user_1_bio.id),
                    "type": "user_bio",
                    "attributes": user_bio_data.dict(),
                },
                "meta": None,
            },
            {
                "data": {
                    "id": str(user_1.id),
                    "type": "user",
                    "attributes": user_data.dict(),
                },
                "meta": None,
            },
        ]

    async def test_create_and_update_atomic_rollback(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        user_1: User,
        user_2: User,
        user_1_bio: UserBio,
    ):
        """

        - create computer (ok)
        - update user bio (ok)
        - update username (not ok, error, rollback)

        :param client:
        :param async_session:
        :param user_1:
        :param user_2:
        :param user_1_bio:
        :return:
        """
        user_data = UserAttributesBaseSchema.from_orm(user_1)
        user_bio_data = UserBioBaseSchema.from_orm(user_1_bio)
        user_bio_data.favourite_movies = fake.sentence()
        assert user_1_bio.favourite_movies != user_bio_data.favourite_movies
        user_data.name = user_2.name
        user_1_name: str = user_1.name
        user_bio_movies: str = user_1_bio.favourite_movies
        assert user_data.name != user_1.name
        new_computer = ComputerAttributesBaseSchema(
            name=fake.user_name(),
        )
        data_atomic_request = {
            "atomic:operations": [
                {
                    "op": "add",
                    "data": {
                        "type": "computer",
                        "attributes": new_computer.dict(),
                        "relationships": {
                            "user": {
                                "data": {
                                    "id": user_1.id,
                                    "type": "user",
                                },
                            },
                        },
                    },
                },
                {
                    "op": "update",
                    "data": {
                        "id": str(user_1_bio.id),
                        "type": "user_bio",
                        "attributes": user_bio_data.dict(),
                    },
                },
                {
                    "op": "update",
                    "data": {
                        "id": str(user_1.id),
                        "type": "user",
                        "attributes": user_data.dict(),
                    },
                },
            ],
        }
        response = await client.post("/operations", json=data_atomic_request)
        assert response.status_code == status.HTTP_400_BAD_REQUEST, response.text
        response_data = response.json()
        assert "errors" in response_data, response_data
        errors = response_data["errors"]
        assert errors
        await async_session.refresh(user_1)
        await async_session.refresh(user_1_bio)
        assert user_1.name != user_data.name
        assert user_1.name == user_1_name
        assert user_1_bio.favourite_movies != user_bio_data.favourite_movies
        assert user_1_bio.favourite_movies == user_bio_movies

        stmt = select(count(Computer.id)).where(Computer.user_id == user_1.id)
        cnt = await async_session.scalar(stmt)
        assert cnt == 0, "no computers have to be created"
        assert errors == [
            {
                "detail": "Object update error",
                "source": {"pointer": "/data"},
                "status_code": status.HTTP_400_BAD_REQUEST,
                "title": "Bad Request",
                "meta": {
                    "id": str(user_1.id),
                    "type": "user",
                },
            },
        ]
