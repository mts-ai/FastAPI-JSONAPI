import pytest
import simplejson as json
from fastapi import FastAPI, status
from httpx import AsyncClient
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from tests.common import IS_POSTGRES
from tests.fixtures.app import build_app_custom
from tests.misc.utils import fake
from tests.models import (
    UserBio,
)
from tests.schemas import UserBioAttributesBaseSchema

pytestmark = pytest.mark.asyncio


class UserBioMeta(BaseModel):
    spam_and_eggs: str


class UserBioJsonMetaSchema(UserBioAttributesBaseSchema):
    meta: UserBioMeta


@pytest.mark.skipif(not IS_POSTGRES, reason="only for pg (for now)")
class TestPostgresFilterByInnerSchema:
    """
    Todo:
    ----
    To create tests for fields:
    - json
    - jsonb
    """

    @pytest.fixture()
    def resource_type(self) -> str:
        return "user_bio_custom_json_meta"

    @pytest.fixture()
    def app(self, resource_type):
        app = build_app_custom(
            model=UserBio,
            schema=UserBioJsonMetaSchema,
            resource_type=resource_type,
            path=f"/{resource_type}",
        )
        return app

    async def test_filter_inner_json_field(
        self,
        app: FastAPI,
        resource_type: str,
        client: AsyncClient,
        async_session: AsyncSession,
        user_1_bio: UserBio,
        user_2_bio: UserBio,
    ):
        # Declared as UserBioMeta.spam_and_eggs
        some_key = "spam_and_eggs"
        # todo: use sentence and take part to check ilike using %{part}%
        value_1 = fake.word()
        value_2 = fake.word()
        assert value_1 != value_2
        assert user_1_bio.id != user_2_bio.id

        await async_session.refresh(user_1_bio)
        await async_session.refresh(user_2_bio)

        # re-assign meta dict! sqla doesn't watch mutations
        user_1_bio.meta = {some_key: value_1}
        user_2_bio.meta = {some_key: value_2}
        await async_session.commit()

        filter_inner = {
            "name": f"meta.{some_key}",
            "op": "ilike",
            "val": value_1,
        }
        query_params = {
            "filter": json.dumps(
                [
                    filter_inner,
                ],
            ),
        }
        url = app.url_path_for(f"get_{resource_type}_list")
        res = await client.get(url, params=query_params)
        assert res.status_code == status.HTTP_200_OK, res.text
        assert res.json() == {
            "data": [
                {
                    "id": str(user_1_bio.id),
                    "type": resource_type,
                    "attributes": UserBioJsonMetaSchema.from_orm(user_1_bio).dict(),
                },
            ],
            "jsonapi": {"version": "1.0"},
            "meta": {"count": 1, "totalPages": 1},
        }
