from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_jsonapi import SqlalchemyDataLayer
from fastapi_jsonapi.views.detail_view import DetailViewBase
from fastapi_jsonapi.views.list_view import ListViewBase


class GenericViewInitializationError(Exception):
    pass


def raise_view_initialization_error():
    msg = (
        "You have to inject session dependency to start using view. "
        'Please override "init_dependencies" in your view class.'
        "See examples on GitHub"
    )
    raise GenericViewInitializationError(msg)


class SqlaViewMixin:
    """
    SQL Alchemy mixin for views

    override init_dependencies, set session

    Make sure to add mixin first (due to mro)
    """

    data_layer_cls = SqlalchemyDataLayer
    session: AsyncSession

    async def init_dependencies(self, session: AsyncSession = Depends(raise_view_initialization_error)):
        self.session = session

    def get_data_layer_kwargs(self):
        return {"session": self.session}


class DetailViewBaseGeneric(
    SqlaViewMixin,
    DetailViewBase,
):
    pass


class ListViewBaseGeneric(
    SqlaViewMixin,
    ListViewBase,
):
    pass
