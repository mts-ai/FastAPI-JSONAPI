from fastapi import Depends
from fastapi.params import Depends as DependsParams
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_jsonapi import RoutersJSONAPI, SqlalchemyEngine
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

    def check_session_dependency(self):
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
    session_dependency: DependsParams = dummy_dependency

    def __init__(self, jsonapi: RoutersJSONAPI, **options):
        super().__init__(jsonapi=jsonapi, **options)
        self.check_session_dependency()

        try:
            getattr(self, "get")
        except AttributeError:

            async def get(
                obj_id,
                query_params: QueryStringManager = Depends(QueryStringManager),
                session: AsyncSession = self.session_dependency,
            ) -> JSONAPIResultDetailSchema:
                dl = SqlalchemyEngine(
                    schema=self.jsonapi.schema_detail,
                    model=self.jsonapi.model,
                    session=session,
                )
                view_kwargs = {"id": obj_id}
                return await self.get_detailed_result(
                    dl=dl,
                    view_kwargs=view_kwargs,
                    query_params=query_params,
                )

            self.get = get


class ListViewBaseGeneric(
    ListViewBase,
    ValidateSessionDependencyMixin,
):
    session_dependency: DependsParams = dummy_dependency

    def __init__(self, jsonapi: RoutersJSONAPI, **options):
        super().__init__(jsonapi=jsonapi, **options)
        self.check_session_dependency()

        try:
            getattr(self, "get")
        except AttributeError:

            async def get(
                query_params: QueryStringManager = Depends(QueryStringManager),
                session: AsyncSession = self.session_dependency,
            ) -> JSONAPIResultListSchema:
                dl = SqlalchemyEngine(
                    schema=self.jsonapi.schema_list,
                    model=self.jsonapi.model,
                    session=session,
                )
                return await self.get_paginated_result(
                    dl=dl,
                    query_params=query_params,
                )

            self.get = get
