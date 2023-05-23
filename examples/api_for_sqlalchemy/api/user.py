from http import HTTPStatus

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from examples.api_for_sqlalchemy.extensions.sqlalchemy import Connector
from examples.api_for_sqlalchemy.helpers.factories.meta_base import FactoryUseMode
from examples.api_for_sqlalchemy.helpers.factories.user import ErrorCreateUserObject, UserFactory
from examples.api_for_sqlalchemy.helpers.updaters.exceptions import ObjectNotFound
from examples.api_for_sqlalchemy.helpers.updaters.update_user import ErrorUpdateUserObject, UpdateUser
from examples.api_for_sqlalchemy.models import User
from examples.api_for_sqlalchemy.models.schemas import UserPatchSchema, UserSchema
from examples.api_for_sqlalchemy.models.schemas.user import UserInSchema
from fastapi_jsonapi import SqlalchemyEngine
from fastapi_jsonapi.exceptions import (
    BadRequest,
    HTTPException,
)
from fastapi_jsonapi.querystring import QueryStringManager
from fastapi_jsonapi.schema import JSONAPIResultDetailSchema, JSONAPIResultListSchema
from fastapi_jsonapi.views.detail_view import DetailViewBase
from fastapi_jsonapi.views.list_view import ListViewBase


class UserDetail(DetailViewBase):
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

    @classmethod
    async def patch(
        cls,
        obj_id,
        data: UserPatchSchema,
        query_params: QueryStringManager,
        session: AsyncSession = Depends(Connector.get_session),
    ) -> UserSchema:
        user_obj: User
        try:
            user_obj = await UpdateUser.update(
                obj_id,
                data.dict(exclude_unset=True),
                query_params.headers,
                session=session,
            )
        except ErrorUpdateUserObject as ex:
            raise BadRequest(ex.description, ex.field)
        except ObjectNotFound as ex:
            raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=ex.description)

        user = UserSchema.from_orm(user_obj)
        return user


class UserList(ListViewBase):
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
        data: UserInSchema,
        query_params: QueryStringManager,
        session: AsyncSession = Depends(Connector.get_session),
    ) -> JSONAPIResultDetailSchema:
        try:
            user_obj = await UserFactory.create(
                data=data.dict(),
                mode=FactoryUseMode.production,
                header=query_params.headers,
                session=session,
            )
        except ErrorCreateUserObject as ex:
            raise BadRequest(ex.description, ex.field)

        dl = SqlalchemyEngine(
            schema=self.jsonapi.schema_detail,
            model=self.jsonapi.model,
            session=session,
        )
        view_kwargs = {"id": user_obj.id}
        return await self.get_detailed_result(
            dl=dl,
            view_kwargs=view_kwargs,
            query_params=query_params,
        )
