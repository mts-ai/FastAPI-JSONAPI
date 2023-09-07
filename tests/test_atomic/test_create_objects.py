import logging

import pytest
from httpx import AsyncClient
from pytest import mark  # noqa
from sqlalchemy import and_, or_, select
from sqlalchemy.engine import Result
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.functions import count
from starlette import status

from tests.misc.utils import fake
from tests.models import User, UserBio
from tests.schemas import ComputerAttributesBaseSchema, UserAttributesBaseSchema, UserBioAttributesBaseSchema

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

    async def test_create_bio_with_relationship_to_user_to_one(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        user_1: User,
    ):
        user_bio = UserBioAttributesBaseSchema(
            birth_city=fake.city(),
            favourite_movies=fake.sentence(),
        )
        stmt_bio = select(UserBio).where(UserBio.user_id == user_1.id)
        res: Result = await async_session.execute(stmt_bio)
        assert res.scalar_one_or_none() is None, "user has to be w/o bio"

        data_atomic_request = {
            "atomic:operations": [
                {
                    "op": "add",
                    "data": {
                        "type": "user_bio",
                        "attributes": user_bio.dict(),
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
            ],
        }
        response = await client.post("/operations", json=data_atomic_request)
        assert response.status_code == status.HTTP_200_OK, response.text
        resp_data = response.json()
        assert resp_data
        results = resp_data["atomic:results"]
        assert len(results) == 1, results
        result_bio_data = results[0]
        res: Result = await async_session.execute(stmt_bio)
        user_bio_created: UserBio = res.scalar_one()
        assert user_bio == UserBioAttributesBaseSchema.from_orm(user_bio_created)
        assert result_bio_data == {
            "data": {
                "attributes": user_bio.dict(),
                "type": "user_bio",
                "id": str(user_bio_created.id),
            },
            "meta": None,
        }

    async def test_create_user_and_user_bio_with_local_id(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
    ):
        """
        - create user
        - create bio for that user

        :param client:
        :param async_session:
        :return:
        """
        user_data = UserAttributesBaseSchema(
            name=fake.name(),
            age=fake.pyint(min_value=13, max_value=99),
            email=fake.email(),
        )
        user_bio_data = UserBioAttributesBaseSchema(
            birth_city=fake.city(),
            favourite_movies=fake.sentence(),
        )

        user_stmt = (
            select(User)
            # find such user
            .where(
                *(
                    # all attrs match
                    getattr(User, attr) == value
                    # all model data
                    for attr, value in user_data
                ),
            )
            # joins
            .options(
                # with bio
                joinedload(User.bio),
            )
        )
        user = await async_session.scalar(user_stmt)
        assert user is None

        user_lid = fake.word()
        data_atomic_request = {
            "atomic:operations": [
                {
                    "op": "add",
                    "data": {
                        "type": "user",
                        "lid": user_lid,
                        "attributes": user_data.dict(),
                    },
                },
                {
                    "op": "add",
                    "data": {
                        "type": "user_bio",
                        "attributes": user_bio_data.dict(),
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
        user = await async_session.scalar(user_stmt)
        assert isinstance(user, User)
        assert isinstance(user.bio, UserBio)

        assert response_data == {
            "atomic:results": [
                {
                    "data": {
                        "id": str(user.id),
                        "type": "user",
                        "attributes": user_data.dict(),
                    },
                    "meta": None,
                },
                {
                    "data": {
                        "id": str(user.bio.id),
                        "type": "user_bio",
                        "attributes": user_bio_data.dict(),
                    },
                    "meta": None,
                },
            ],
        }

    async def test_create_user_and_create_computer_for_user(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
    ):
        """

        - create user
        - create computer for this created user

        :param client:
        :param async_session:
        :return:
        """
        user_data = UserAttributesBaseSchema(
            name=fake.name(),
            age=fake.pyint(min_value=13, max_value=99),
            email=fake.email(),
        )
        computer_data = ComputerAttributesBaseSchema(
            name=fake.word(),
        )

        user_stmt = (
            select(User)
            # find such user
            .where(
                *(
                    # all attrs match
                    getattr(User, attr) == value
                    # all model data
                    for attr, value in user_data
                ),
            )
            # joins
            .options(
                # with computers
                joinedload(User.computers),
            )
        )
        user = await async_session.scalar(user_stmt)
        assert user is None

        user_lid = fake.word()
        data_atomic_request = {
            "atomic:operations": [
                {
                    "op": "add",
                    "data": {
                        "type": "user",
                        "lid": user_lid,
                        "attributes": user_data.dict(),
                    },
                },
                {
                    "op": "add",
                    "data": {
                        "type": "computer",
                        "attributes": computer_data.dict(),
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
        user = await async_session.scalar(user_stmt)
        assert isinstance(user, User)
        assert user.computers
        assert len(user.computers) == 1

        assert response_data == {
            "atomic:results": [
                {
                    "data": {
                        "id": str(user.id),
                        "type": "user",
                        "attributes": user_data.dict(),
                    },
                    "meta": None,
                },
                {
                    "data": {
                        "id": str(user.computers[0].id),
                        "type": "computer",
                        "attributes": computer_data.dict(),
                    },
                    "meta": None,
                },
            ],
        }

    async def test_create_user_and_create_bio_and_computer_for_user(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
    ):
        """

        - create user
        - create bio for user
        - create computer for this created user

        :param client:
        :param async_session:
        :return:
        """
        user_data = UserAttributesBaseSchema(
            name=fake.name(),
            age=fake.pyint(min_value=13, max_value=99),
            email=fake.email(),
        )
        user_bio_data = UserBioAttributesBaseSchema(
            birth_city=fake.city(),
            favourite_movies=fake.sentence(),
        )
        computer_data = ComputerAttributesBaseSchema(
            name=fake.word(),
        )

        user_stmt = (
            select(User)
            # find such user
            .where(
                *(
                    # all attrs match
                    getattr(User, attr) == value
                    # all model data
                    for attr, value in user_data
                ),
            )
            # joins
            .options(
                # with bio
                joinedload(User.bio),
                joinedload(User.computers),
            )
        )
        user = await async_session.scalar(user_stmt)
        assert user is None

        user_lid = fake.word()
        data_atomic_request = {
            "atomic:operations": [
                {
                    "op": "add",
                    "data": {
                        "type": "user",
                        "lid": user_lid,
                        "attributes": user_data.dict(),
                    },
                },
                {
                    "op": "add",
                    "data": {
                        "type": "user_bio",
                        "attributes": user_bio_data.dict(),
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
                {
                    "op": "add",
                    "data": {
                        "type": "computer",
                        "attributes": computer_data.dict(),
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
        user = await async_session.scalar(user_stmt)
        assert isinstance(user, User)
        assert isinstance(user.bio, UserBio)
        assert user.computers
        assert len(user.computers) == 1

        assert response_data == {
            "atomic:results": [
                {
                    "data": {
                        "id": str(user.id),
                        "type": "user",
                        "attributes": user_data.dict(),
                    },
                    "meta": None,
                },
                {
                    "data": {
                        "id": str(user.bio.id),
                        "type": "user_bio",
                        "attributes": user_bio_data.dict(),
                    },
                    "meta": None,
                },
                {
                    "data": {
                        "id": str(user.computers[0].id),
                        "type": "computer",
                        "attributes": computer_data.dict(),
                    },
                    "meta": None,
                },
            ],
        }

    async def test_resource_type_with_local_id_not_found(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
    ):
        """

        - create user
        - create computer for this created user

        :param client:
        :param async_session:
        :return:
        """
        user_data = UserAttributesBaseSchema(
            name=fake.name(),
            age=fake.pyint(min_value=13, max_value=99),
            email=fake.email(),
        )
        computer_data = ComputerAttributesBaseSchema(
            name=fake.word(),
        )

        user_stmt = (
            select(User)
            # find such user
            .where(
                *(
                    # all attrs match
                    getattr(User, attr) == value
                    # all model data
                    for attr, value in user_data
                ),
            )
            # joins
            .options(
                # with computers
                joinedload(User.computers),
            )
        )
        user = await async_session.scalar(user_stmt)
        assert user is None

        user_lid = fake.word()
        relation_type = "user"
        relationship_info = {
            "lid": user_lid,
            "type": relation_type,
        }
        data_atomic_request = {
            "atomic:operations": [
                {
                    "op": "add",
                    "data": {
                        "type": "user",
                        "attributes": user_data.dict(),
                    },
                },
                {
                    "op": "add",
                    "data": {
                        "type": "computer",
                        "attributes": computer_data.dict(),
                        "relationships": {
                            "user": {
                                "data": relationship_info,
                            },
                        },
                    },
                },
            ],
        }

        expected_error_text = (
            f"Resource {relation_type} not found in previous operations, "
            f"no lid {user_lid} defined yet, cannot create {relationship_info}"
        )

        with pytest.raises(ValueError, match=expected_error_text):
            # TODO: where's http exception?
            await client.post("/operations", json=data_atomic_request)

        user = await async_session.scalar(user_stmt)
        assert user is None

    async def test_local_id_not_found(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
    ):
        """

        - create user
        - create computer for this created user

        :param client:
        :param async_session:
        :return:
        """
        user_data = UserAttributesBaseSchema(
            name=fake.name(),
            age=fake.pyint(min_value=13, max_value=99),
            email=fake.email(),
        )
        computer_data = ComputerAttributesBaseSchema(
            name=fake.word(),
        )

        user_stmt = (
            select(User)
            # find such user
            .where(
                *(
                    # all attrs match
                    getattr(User, attr) == value
                    # all model data
                    for attr, value in user_data
                ),
            )
            # joins
            .options(
                # with computers
                joinedload(User.computers),
            )
        )
        user = await async_session.scalar(user_stmt)
        assert user is None

        user_lid = fake.word()
        another_lid = fake.word()
        assert user_lid != another_lid
        relation_type = "user"
        relationship_info = {
            "lid": another_lid,
            "type": relation_type,
        }
        data_atomic_request = {
            "atomic:operations": [
                {
                    "op": "add",
                    "data": {
                        "type": "user",
                        "lid": user_lid,
                        "attributes": user_data.dict(),
                    },
                },
                {
                    "op": "add",
                    "data": {
                        "type": "computer",
                        "attributes": computer_data.dict(),
                        "relationships": {
                            "user": {
                                "data": relationship_info,
                            },
                        },
                    },
                },
            ],
        }

        expected_error_text = (
            f"lid {another_lid} for {relation_type} not found"
            f" in previous operations, cannot process {relationship_info}"
        )
        with pytest.raises(ValueError, match=expected_error_text):
            # TODO: where's http exception?
            await client.post("/operations", json=data_atomic_request)

        user = await async_session.scalar(user_stmt)
        assert user is None

    @pytest.mark.skip("not ready yet")
    async def test_update_to_many_relationship_with_local_id(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
    ):
        """
        - create post
        - update post relationship to have new comment

        :param client:
        :param async_session:
        :return:
        """
