import logging
from typing import Callable, Sequence

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
from tests.models import Child, Parent, ParentToChildAssociation, User, UserBio
from tests.schemas import (
    ChildAttributesSchema,
    ComputerAttributesBaseSchema,
    ParentAttributesSchema,
    ParentToChildAssociationAttributesSchema,
    UserAttributesBaseSchema,
    UserBioAttributesBaseSchema,
)

COLUMN_CHARACTERS_LIMIT = 50

pytestmark = mark.asyncio

logging.basicConfig(level=logging.DEBUG)


def random_sentence() -> str:
    return fake.sentence()[:COLUMN_CHARACTERS_LIMIT]


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
        user_attributes: UserAttributesBaseSchema,
    ):
        user = user_attributes
        data_atomic_request = {
            "atomic:operations": [
                {
                    "op": "add",
                    "data": {
                        "type": "user",
                        "attributes": user.model_dump(),
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
                "attributes": UserAttributesBaseSchema.model_validate(user_obj).model_dump(),
                "id": str(user_obj.id),
                "type": "user",
            },
        }

    async def test_create_two_objects(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        user_attributes_factory: Callable[[], UserAttributesBaseSchema],
    ):
        user_data_1 = user_attributes_factory()
        user_data_2 = user_attributes_factory()
        users_data = [user_data_1, user_data_2]
        data_atomic_request = {
            "atomic:operations": [
                {
                    "op": "add",
                    "data": {
                        "type": "user",
                        "attributes": user_data.model_dump(),
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
        users: Sequence[User] = db_result.scalars().all()
        assert len(users) == len(results)
        for result, user in zip(results, users):
            assert result.pop("meta") is None
            assert result == {
                "data": {
                    "attributes": UserAttributesBaseSchema.model_validate(user).model_dump(),
                    "id": str(user.id),
                    "type": "user",
                },
            }

    async def test_atomic_rollback_on_create_error(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        user_attributes_factory: Callable[[], UserAttributesBaseSchema],
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
        user_data_1 = user_attributes_factory()
        user_data_2 = user_attributes_factory()
        user_data_2.name = user_data_1.name
        users_data = [user_data_1, user_data_2]
        data_atomic_request = {
            "atomic:operations": [
                {
                    "op": "add",
                    "data": {
                        "type": "user",
                        "attributes": user_data.model_dump(),
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
            favourite_movies=random_sentence(),
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
                        "attributes": user_bio.model_dump(),
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
        assert user_bio == UserBioAttributesBaseSchema.model_validate(user_bio_created)
        assert result_bio_data == {
            "data": {
                "attributes": user_bio.model_dump(),
                "type": "user_bio",
                "id": str(user_bio_created.id),
            },
            "meta": None,
        }

    async def test_create_user_and_user_bio_with_local_id(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        user_attributes: UserAttributesBaseSchema,
    ):
        """
        Prepare test data:

        - create user
        - create bio for that user

        :param client:
        :param async_session:
        :return:
        """
        user_data = user_attributes
        user_bio_data = UserBioAttributesBaseSchema(
            birth_city=fake.city(),
            favourite_movies=random_sentence(),
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
                        "attributes": user_data.model_dump(),
                    },
                },
                {
                    "op": "add",
                    "data": {
                        "type": "user_bio",
                        "attributes": user_bio_data.model_dump(),
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
                        "attributes": user_data.model_dump(),
                    },
                    "meta": None,
                },
                {
                    "data": {
                        "id": str(user.bio.id),
                        "type": "user_bio",
                        "attributes": user_bio_data.model_dump(),
                    },
                    "meta": None,
                },
            ],
        }

    async def test_create_user_and_create_computer_for_user(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        user_attributes: UserAttributesBaseSchema,
    ):
        """
        Prepare test data:

        - create user
        - create computer for this created user

        :param client:
        :param async_session:
        :return:
        """
        user_data = user_attributes
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
                        "attributes": user_data.model_dump(),
                    },
                },
                {
                    "op": "add",
                    "data": {
                        "type": "computer",
                        "attributes": computer_data.model_dump(),
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
                        "attributes": user_data.model_dump(),
                    },
                    "meta": None,
                },
                {
                    "data": {
                        "id": str(user.computers[0].id),
                        "type": "computer",
                        "attributes": computer_data.model_dump(),
                    },
                    "meta": None,
                },
            ],
        }

    async def test_create_user_and_create_bio_and_computer_for_user(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        user_attributes: UserAttributesBaseSchema,
    ):
        """
        Prepare test data:

        - create user
        - create bio for user
        - create computer for this created user

        :param client:
        :param async_session:
        :return:
        """
        user_data = user_attributes
        user_bio_data = UserBioAttributesBaseSchema(
            birth_city=fake.city(),
            favourite_movies=random_sentence(),
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
                        "attributes": user_data.model_dump(),
                    },
                },
                {
                    "op": "add",
                    "data": {
                        "type": "user_bio",
                        "attributes": user_bio_data.model_dump(),
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
                        "attributes": computer_data.model_dump(),
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
                        "attributes": user_data.model_dump(),
                    },
                    "meta": None,
                },
                {
                    "data": {
                        "id": str(user.bio.id),
                        "type": "user_bio",
                        "attributes": user_bio_data.model_dump(),
                    },
                    "meta": None,
                },
                {
                    "data": {
                        "id": str(user.computers[0].id),
                        "type": "computer",
                        "attributes": computer_data.model_dump(),
                    },
                    "meta": None,
                },
            ],
        }

    async def test_resource_type_with_local_id_not_found(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        user_attributes: UserAttributesBaseSchema,
    ):
        """
        Prepare test data:

        - create user
        - create computer for this created user

        :param client:
        :param async_session:
        :return:
        """
        user_data = user_attributes
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

        action_1 = {
            "op": "add",
            "data": {
                "type": "user",
                "attributes": user_data.model_dump(),
            },
        }
        action_2 = {
            "op": "add",
            "data": {
                "type": "computer",
                "attributes": computer_data.model_dump(),
                "relationships": {
                    "user": {
                        "data": relationship_info,
                    },
                },
            },
        }
        data_atomic_request = {
            "atomic:operations": [
                action_1,
                action_2,
            ],
        }

        expected_error_text = (
            f"Resource {relation_type!r} not found in previous operations, "
            f"no lid {user_lid!r} defined yet, cannot create {relationship_info}"
        )

        response = await client.post("/operations", json=data_atomic_request)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, response.text
        assert response.json() == {
            "detail": {
                "data": {
                    **action_2["data"],
                    "id": None,
                    "lid": None,
                },
                "error": expected_error_text,
                "message": f"Validation error on operation {action_1['op']}",
                "ref": None,
            },
        }

        user = await async_session.scalar(user_stmt)
        assert user is None

    async def test_local_id_not_found(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        user_attributes: UserAttributesBaseSchema,
    ):
        """
        Prepare test data:

        - create user
        - create computer for this created user

        :param client:
        :param async_session:
        :return:
        """
        user_data = user_attributes
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
        action_1 = {
            "op": "add",
            "data": {
                "type": "user",
                "lid": user_lid,
                "attributes": user_data.model_dump(),
            },
        }
        action_2 = {
            "op": "add",
            "data": {
                "type": "computer",
                "attributes": computer_data.model_dump(),
                "relationships": {
                    "user": {
                        "data": relationship_info,
                    },
                },
            },
        }
        data_atomic_request = {
            "atomic:operations": [
                action_1,
                action_2,
            ],
        }

        expected_error_text = (
            f"lid {another_lid!r} for {relation_type!r} not found"
            f" in previous operations, cannot process {relationship_info}"
        )
        response = await client.post("/operations", json=data_atomic_request)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, response.text
        assert response.json() == {
            "detail": {
                "data": {
                    **action_2["data"],
                    "id": None,
                    "lid": None,
                },
                "error": expected_error_text,
                "message": f"Validation error on operation {action_2['op']}",
                "ref": None,
            },
        }

        user = await async_session.scalar(user_stmt)
        assert user is None

    async def test_create_and_associate_many_to_many(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
    ):
        parent_data = ParentAttributesSchema(name=fake.name())
        child_data = ChildAttributesSchema(name=fake.name())
        association_extra_data = random_sentence()

        data_atomic_request = {
            "atomic:operations": [
                # create parent
                {
                    "op": "add",
                    "data": {
                        "lid": "new-parent",
                        "type": "parent",
                        "attributes": parent_data.model_dump(),
                    },
                },
                # create child
                {
                    "op": "add",
                    "data": {
                        "lid": "new-child",
                        "type": "child",
                        "attributes": child_data.model_dump(),
                    },
                },
                # create parent-to-child association
                {
                    "op": "add",
                    "data": {
                        "type": "parent-to-child-association",
                        "attributes": {
                            "extra_data": association_extra_data,
                        },
                        "relationships": {
                            "parent": {
                                "data": {
                                    "lid": "new-parent",
                                    "type": "parent",
                                },
                            },
                            "child": {
                                "data": {
                                    "lid": "new-child",
                                    "type": "child",
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

        stmt = (
            select(ParentToChildAssociation)
            .join(ParentToChildAssociation.parent)
            .join(ParentToChildAssociation.child)
            .where(
                ParentToChildAssociation.extra_data == association_extra_data,
                Parent.name == parent_data.name,
                Child.name == child_data.name,
            )
            .options(
                joinedload(ParentToChildAssociation.parent),
                joinedload(ParentToChildAssociation.child),
            )
        )
        result: Result = await async_session.execute(stmt)
        assoc: ParentToChildAssociation = result.scalar_one()

        assert isinstance(assoc.parent, Parent)
        assert isinstance(assoc.child, Child)

        assert response_data == {
            "atomic:results": [
                {
                    "data": {
                        "attributes": ParentAttributesSchema.model_validate(assoc.parent).model_dump(),
                        "id": str(assoc.parent.id),
                        "type": "parent",
                    },
                    "meta": None,
                },
                {
                    "data": {
                        "attributes": ChildAttributesSchema.model_validate(assoc.child).model_dump(),
                        "id": str(assoc.child.id),
                        "type": "child",
                    },
                    "meta": None,
                },
                {
                    "data": {
                        "attributes": ParentToChildAssociationAttributesSchema.model_validate(assoc).model_dump(),
                        "id": str(assoc.id),
                        "type": "parent-to-child-association",
                    },
                    "meta": None,
                },
            ],
        }

    async def test_create_object_schema_validation_error(
        self,
        client: AsyncClient,
    ):
        action_add = {
            "op": "add",
            "data": {
                "type": "user",
                # not passing the required `name` attribute
                "attributes": {},
            },
        }
        data_atomic_request = {
            "atomic:operations": [
                action_add,
            ],
        }

        response = await client.post("/operations", json=data_atomic_request)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, response.text
        # TODO: json:api exception
        assert response.json() == {
            "detail": {
                "data": {
                    **action_add["data"],
                    "id": None,
                    "lid": None,
                    "relationships": None,
                },
                "errors": [
                    {
                        "loc": ["data", "attributes", "name"],
                        "msg": "field required",
                        "type": "value_error.missing",
                    },
                ],
                "message": f"Validation error on operation {action_add['op']}",
                "ref": None,
            },
        }

    @pytest.mark.skip("not ready yet")
    async def test_update_to_many_relationship_with_local_id(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
    ):
        """
        Prepare test data:

        - create post
        - update post relationship to have new comment

        :param client:
        :param async_session:
        :return:
        """
