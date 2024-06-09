import logging

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from tests.misc.utils import fake
from tests.models import Computer, User, UserBio
from tests.schemas import UserAttributesBaseSchema, UserBioAttributesBaseSchema

pytestmark = pytest.mark.asyncio

logging.basicConfig(level=logging.DEBUG)


class TestAtomicUpdateObjects:
    async def test_update_two_objects(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        user_1: User,
        user_1_bio: UserBio,
    ):
        user_data = UserAttributesBaseSchema.model_validate(user_1)
        user_bio_data = UserBioAttributesBaseSchema.model_validate(user_1_bio)
        user_data.name = fake.name()
        user_bio_data.favourite_movies = fake.sentence()
        assert user_1.name != user_data.name
        assert user_1_bio.favourite_movies != user_bio_data.favourite_movies
        data_atomic_request = {
            "atomic:operations": [
                {
                    "op": "update",
                    "data": {
                        "id": str(user_1.id),
                        "type": "user",
                        "attributes": user_data.model_dump(),
                    },
                },
                {
                    "op": "update",
                    "data": {
                        "id": str(user_1_bio.id),
                        "type": "user_bio",
                        "attributes": user_bio_data.model_dump(),
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

        assert results == [
            {
                "data": {
                    "attributes": user_data.model_dump(),
                    "id": str(user_1.id),
                    "type": "user",
                },
                "meta": None,
            },
            {
                "data": {
                    "attributes": user_bio_data.model_dump(),
                    "id": str(user_1_bio.id),
                    "type": "user_bio",
                },
                "meta": None,
            },
        ]

    @pytest.mark.skip("todo: create relationships resources")
    async def test_update_to_one_relationship_atomic(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        user_1: User,
        computer_1: Computer,
    ):
        """
        as in doc:

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
        :param user_1:
        :param computer_1:
        :return:
        """
        assert computer_1.user_id is None
        operation_data = {
            "atomic:operations": [
                {
                    "op": "update",
                    "ref": {
                        "type": "computer",
                        "id": computer_1.id,
                        "relationship": "user",
                    },
                    "data": {
                        "type": "user",
                        "id": user_1.id,
                    },
                },
            ],
        }

        response = await client.post("/operations", json=operation_data)
        assert response.status_code == status.HTTP_200_OK, response.text

        await async_session.refresh(computer_1)
        assert computer_1.user_id == user_1.id

    @pytest.mark.skip("todo: create relationships resources")
    async def test_update_to_one_relationship_clear_atomic(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        user_1: User,
        computer_1: Computer,
    ):
        """
        # TODO: relationships resources

        # as in doc
        https://jsonapi.org/ext/atomic/#auto-id-updating-to-one-relationships
        {
          "atomic:operations": [{
            "op": "update",
            "ref": {
              "type": "articles",
              "id": "13",
              "relationship": "author"
            },
            "data": null
          }]
        }

        :param client:
        :param async_session:
        :param user_1:
        :param computer_1:
        :return:
        """
        computer_1.user_id = user_1.id
        await async_session.commit()
        await async_session.refresh(computer_1)
        assert computer_1.user_id == user_1.id

        operation_data = {
            "atomic:operations": [
                {
                    "op": "update",
                    "ref": {
                        "type": "computer",
                        "id": computer_1.id,
                        "relationship": "author",
                    },
                    "data": None,
                },
            ],
        }

        response = await client.post("/operations", json=operation_data)
        assert response.status_code == status.HTTP_200_OK, response.text

        await async_session.refresh(computer_1)
        assert computer_1.user_id == user_1.id
