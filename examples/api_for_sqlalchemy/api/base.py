from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from examples.api_for_sqlalchemy.extensions.sqlalchemy import Connector
from fastapi_jsonapi import SqlalchemyEngine
from fastapi_jsonapi.querystring import QueryStringManager
from fastapi_jsonapi.schema import JSONAPIResultDetailSchema, JSONAPIResultListSchema
from fastapi_jsonapi.views.detail_view import DetailViewBase
from fastapi_jsonapi.views.list_view import ListViewBase


class DetailViewBaseGeneric(DetailViewBase):
    async def get(
        self,
        obj_id,
        query_params: QueryStringManager,
        session: AsyncSession = Depends(Connector.get_session),
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


class ListViewBaseGeneric(ListViewBase):
    async def get(
        self,
        query_params: QueryStringManager,
        session: AsyncSession = Depends(Connector.get_session),
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
