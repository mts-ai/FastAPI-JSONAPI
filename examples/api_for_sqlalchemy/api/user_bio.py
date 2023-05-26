from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from examples.api_for_sqlalchemy.extensions.sqlalchemy import Connector
from examples.api_for_sqlalchemy.helpers.factories.meta_base import FactoryUseMode
from examples.api_for_sqlalchemy.helpers.factories.user_bio import ErrorCreateUserBioObject, UserBioFactory
from examples.api_for_sqlalchemy.models import UserBio
from examples.api_for_sqlalchemy.models.schemas.user_bio import UserBioInSchema
from fastapi_jsonapi import SqlalchemyEngine
from fastapi_jsonapi.querystring import QueryStringManager
from fastapi_jsonapi.schema import JSONAPIResultDetailSchema, JSONAPIResultListSchema
from fastapi_jsonapi.views.detail_view import DetailViewBase
from fastapi_jsonapi.views.list_view import ListViewBase


class UserBioDetail(DetailViewBase):
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

    # @classmethod
    # async def patch(
    #     cls,
    #     obj_id,
    #     data: UserBioPatchSchema,
    #     query_params: QueryStringManager,
    #     session: AsyncSession = Depends(Connector.get_session),
    # ) -> UserBioSchema:
    #     user_bio_obj: UserBio
    #     try:
    #         user_bio_obj = await UpdateUserBio.update(
    #             obj_id,
    #             data.dict(exclude_unset=True),
    #             query_params.headers,
    #             session=session,
    #         )
    #     except ErrorUpdateUserBioObject as ex:
    #         raise BadRequest(ex.description, ex.field)
    #     except ObjectNotFound as ex:
    #         raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=ex.description)
    #
    #     user = UserBioSchema.from_orm(user_bio_obj)
    #     return user


class UserBioList(ListViewBase):
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

    async def post(
        self,
        data: UserBioInSchema,
        query_params: QueryStringManager,
        session: AsyncSession = Depends(Connector.get_session),
    ) -> JSONAPIResultDetailSchema:
        user_bio_obj: UserBio = await UserBioFactory.create_object_generic(
            data_as_schema=data,
            query_params=query_params,
            session=session,
            factory_mode=FactoryUseMode.production,
            exc=ErrorCreateUserBioObject,
        )
        dl = SqlalchemyEngine(
            schema=self.jsonapi.schema_detail,
            model=self.jsonapi.model,
            session=session,
        )
        view_kwargs = {"id": user_bio_obj.id}
        return await self.get_detailed_result(
            dl=dl,
            view_kwargs=view_kwargs,
            query_params=query_params,
        )
