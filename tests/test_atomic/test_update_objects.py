import logging

from httpx import AsyncClient
from pytest import mark  # noqa
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from tests.misc.utils import fake
from tests.models import User, UserBio
from tests.schemas import UserAttributesBaseSchema, UserBioAttributesBaseSchema

pytestmark = mark.asyncio

logging.basicConfig(level=logging.DEBUG)


class TestAtomicUpdateObjects:
    async def test_update_two_objects(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        user_1: User,
        user_1_bio: UserBio,
    ):
        user_data = UserAttributesBaseSchema.from_orm(user_1)
        user_bio_data = UserBioAttributesBaseSchema.from_orm(user_1_bio)
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
                        "attributes": user_data.dict(),
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
                    "attributes": user_data.dict(),
                    "id": str(user_1.id),
                    "type": "user",
                },
                "meta": None,
            },
            {
                "data": {
                    "attributes": user_bio_data.dict(),
                    "id": str(user_1_bio.id),
                    "type": "user_bio",
                },
                "meta": None,
            },
        ]
