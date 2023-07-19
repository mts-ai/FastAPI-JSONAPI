from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from examples.api_for_sqlalchemy.extensions.sqlalchemy import Connector
from fastapi_jsonapi.misc.sqla.generics.base import DetailViewBaseGeneric, ListViewBaseGeneric


class SessionDependencyMixin:
    session: AsyncSession

    async def init_dependencies(self, session: AsyncSession = Depends(Connector.get_session)):
        self.session = session


class DetailViewBase(SessionDependencyMixin, DetailViewBaseGeneric):
    """
    Generic view base (detail)
    """


class ListViewBase(SessionDependencyMixin, ListViewBaseGeneric):
    """
    Generic view base (list)
    """
