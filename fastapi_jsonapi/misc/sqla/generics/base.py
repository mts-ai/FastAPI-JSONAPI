from fastapi import Depends
from fastapi.params import Depends as DependsParams
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_jsonapi import RoutersJSONAPI, SqlalchemyDataLayer
from fastapi_jsonapi.querystring import QueryStringManager
from fastapi_jsonapi.schema import JSONAPIResultDetailSchema, JSONAPIResultListSchema
from fastapi_jsonapi.views.detail_view import DetailViewBase
from fastapi_jsonapi.views.list_view import ListViewBase


class GenericViewInitializationError(Exception):
    pass


def build_view_initialization_error(class_name: str) -> GenericViewInitializationError:
    return GenericViewInitializationError(
        "You have to inject session dependency to start using view. "
        f'Please set attribute "session_dependency" for class "{class_name}" as something like '
        f"{class_name}.session_dependency = Depends(AnyCallableWhichReturnAsyncSession)",
    )


dummy_dependency = Depends(lambda: "Dummy")


class ValidateSessionDependencyMixin:
    session_dependency: DependsParams

    def _check_session_dependency(self):
        """Checks that session dependency is a valid argument option acceptable by Fastapi views"""
        if any(
            [
                not isinstance(self.session_dependency, DependsParams),
                self.session_dependency is dummy_dependency,
            ],
        ):
            raise build_view_initialization_error(self.__class__.__name__)


class DetailViewBaseGeneric(
    DetailViewBase,
    ValidateSessionDependencyMixin,
):
    data_layer_cls = SqlalchemyDataLayer
    session_dependency: DependsParams = dummy_dependency

    def __init__(self, jsonapi: RoutersJSONAPI, **options):
        super().__init__(jsonapi=jsonapi, **options)
        self._check_session_dependency()
        self._init_generic_methods()

    def _init_generic_methods(self):
        if not hasattr(self, "get"):

            async def get(
                obj_id,
                query_params: QueryStringManager = Depends(QueryStringManager),
                session: AsyncSession = self.session_dependency,
            ) -> JSONAPIResultDetailSchema:
                view_kwargs = {"id": obj_id}
                return await self.get_view_result(
                    query_params=query_params,
                    view_kwargs=view_kwargs,
                    session=session,
                )

            self.get = get


class ListViewBaseGeneric(
    ListViewBase,
    ValidateSessionDependencyMixin,
):
    data_layer_cls = SqlalchemyDataLayer
    session_dependency: DependsParams = dummy_dependency

    def __init__(self, jsonapi: RoutersJSONAPI, **options):
        super().__init__(jsonapi=jsonapi, **options)
        self._check_session_dependency()
        self._init_generic_methods()

    def _init_generic_methods(self):
        if not hasattr(self, "get"):

            async def get(
                query_params: QueryStringManager = Depends(QueryStringManager),
                session: AsyncSession = self.session_dependency,
            ) -> JSONAPIResultListSchema:
                return await self.get_view_result(
                    query_params=query_params,
                    session=session,
                )

            self.get = get
