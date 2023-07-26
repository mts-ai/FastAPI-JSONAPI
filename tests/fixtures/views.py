from fastapi import Depends
from pytest import fixture  # noqa
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_jsonapi.misc.sqla.generics.base import (
    DetailViewBaseGeneric as DetailViewBaseGenericHelper,
)
from fastapi_jsonapi.misc.sqla.generics.base import (
    ListViewBaseGeneric as ListViewBaseGenericHelper,
)
from tests.fixtures.db_connection import async_session_dependency


class DetailViewBaseGeneric(DetailViewBaseGenericHelper):
    async def init_dependencies(self, session: AsyncSession = Depends(async_session_dependency)):
        self.session = session


class ListViewBaseGeneric(ListViewBaseGenericHelper):
    async def init_dependencies(self, session: AsyncSession = Depends(async_session_dependency)):
        self.session = session
