from __future__ import annotations

import logging
from typing import Awaitable, Callable

import pytest
from httpx import AsyncClient
from pytest import mark  # noqa
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import count
from starlette import status

from tests.misc.utils import fake
from tests.models import Computer, User, UserBio
from tests.schemas import ComputerAttributesBaseSchema, UserAttributesBaseSchema, UserBioAttributesBaseSchema

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
        Prepare test data:

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
        user_bio_data = UserBioAttributesBaseSchema.from_orm(user_1_bio)
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
        Prepare test data:

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
        user_bio_data = UserBioAttributesBaseSchema.from_orm(user_1_bio)
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

    async def test_create_update_and_delete_atomic_success(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        user_1: User,
        user_1_bio: UserBio,
        computer_factory: Callable[..., Awaitable[Computer]],
    ):
        """
        Prepare test data:

        Create computer for user
        Update user's Bio
        Update user
        Delete some other object

        action "remove" doesn't return anything

        :param client:
        :param async_session:
        :param user_1:
        :param user_1_bio:
        :param computer_factory:
        :return:
        """
        computer: Computer = await computer_factory()
        user_data = UserAttributesBaseSchema.from_orm(user_1)
        user_bio_data = UserBioAttributesBaseSchema.from_orm(user_1_bio)
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
                        "id": user_1_bio.id,
                        "type": "user_bio",
                        "attributes": user_bio_data.dict(),
                    },
                },
                {
                    "op": "update",
                    "data": {
                        "id": user_1.id,
                        "type": "user",
                        "attributes": user_data.dict(),
                    },
                },
                {
                    "op": "remove",
                    "ref": {
                        "id": computer.id,
                        "type": "computer",
                    },
                },
            ],
        }
        stmt_comp = select(count(Computer.id)).where(Computer.id == computer.id)
        comp_exists = await async_session.scalar(stmt_comp)
        assert comp_exists == 1
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
            # https://jsonapi.org/ext/atomic/#result-objects
            # An empty result object ({}) is acceptable for operations that are not required to return data.
            # TODO: An empty result object ({})
            # {},
            {
                "data": None,
                "meta": None,
            },
        ]

        comp_exists = await async_session.scalar(stmt_comp)
        assert comp_exists == 0

    async def test_create_user_and_update_computer_and_link_to_user(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        computer_1: Computer,
    ):
        """
        Prepare data:

        Create user
        Update computer, link it to user

        :param client:
        :param async_session:
        :param computer_1:
        :return:
        """
        assert computer_1.user_id is None
        computer_update = ComputerAttributesBaseSchema(
            name=fake.name(),
        )
        user_create = UserAttributesBaseSchema(
            name=fake.name(),
            age=fake.pyint(min_value=13, max_value=99),
            email=fake.email(),
        )
        assert computer_update.name != computer_1.name

        user_lid = fake.word()
        data_atomic_request = {
            "atomic:operations": [
                {
                    "op": "add",
                    "data": {
                        "type": "user",
                        "lid": user_lid,
                        "attributes": user_create.dict(),
                    },
                },
                {
                    "op": "update",
                    "data": {
                        "id": str(computer_1.id),
                        "type": "computer",
                        "attributes": computer_update.dict(),
                        "relationships": {
                            "user": {
                                "data": {
                                    "lid": user_lid,
                                    "type": "user",
                                },
                            },
                        },
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
        user_stmt = (
            select(User)
            # find such user
            .where(
                *(
                    # all attrs match
                    getattr(User, attr) == value
                    # all model data
                    for attr, value in user_create
                ),
            )
        )
        user: User | None = await async_session.scalar(user_stmt)
        assert user
        await async_session.refresh(computer_1)
        assert computer_1.name == computer_update.name
        assert computer_1.user_id == user.id
        assert results == [
            {
                "data": {
                    "id": str(user.id),
                    "type": "user",
                    "attributes": user_create.dict(),
                },
                "meta": None,
            },
            {
                "data": {
                    "id": str(computer_1.id),
                    "type": "computer",
                    "attributes": computer_update.dict(),
                },
                "meta": None,
            },
        ]

    async def test_create_user_and_link_computer_one_operation(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        computer_1: Computer,
    ):
        """
        Create user with relationship to computer

        :param client:
        :param async_session:
        :param computer_1:
        :return:
        """
        assert computer_1.user_id is None
        user_create = UserAttributesBaseSchema(
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
                        "attributes": user_create.dict(),
                        "relationships": {
                            "computers": {
                                "data": [
                                    {
                                        "id": computer_1.id,
                                        "type": "computer",
                                    },
                                ],
                            },
                        },
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
        await async_session.refresh(computer_1)
        user_stmt = (
            select(User)
            # find such user
            .where(
                *(
                    # all attrs match
                    getattr(User, attr) == value
                    # all model data
                    for attr, value in user_create
                ),
            )
        )
        new_user: User | None = await async_session.scalar(user_stmt)
        assert isinstance(new_user, User)
        assert computer_1.user_id == new_user.id
        assert results == [
            {
                "data": {
                    "id": str(new_user.id),
                    "type": "user",
                    "attributes": user_create.dict(),
                },
                "meta": None,
            },
        ]

    @pytest.mark.skip("todo: create relationships resources")
    async def create_user_and_link_existing_computer_to_user(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        computer_1: Computer,
    ):
        """
        Prepare test data:

        - create user
        - update existing computer to be linked to this created user

        # almost like
        https://jsonapi.org/ext/atomic/#auto-id-updating-to-one-relationships
        {
          "atomic:operations": [{
            "op": "update",
            "ref": {
              "type": "articles",
              "id": "13",
              "relationship": "author"
            },
            "data": {
              "type": "people",
              "id": "9"
            }
          }]
        }

        :param client:
        :param async_session:
        :param computer_1:
        :return:
        """
        assert computer_1.user_id is None

    @pytest.mark.skip("todo: create relationships resources")
    async def create_user_and_create_bio_and_link_computer_for_user(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        user_1: User,
        user_1_bio: UserBio,
        computer_1: Computer,
    ):
        """
        Prepare test data:

        - create user
        - create bio for user
        - update existing computer to be linked to this created user

        :param client:
        :param async_session:
        :param user_1:
        :param user_1_bio:
        :param computer_1:
        :return:
        """
