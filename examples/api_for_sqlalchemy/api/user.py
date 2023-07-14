from fastapi import Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from examples.api_for_sqlalchemy.extensions.sqlalchemy import Connector
from examples.api_for_sqlalchemy.helpers.factories.user import ErrorCreateUserObject, UserFactory
from examples.api_for_sqlalchemy.helpers.updaters.update_user import ErrorUpdateUserObject, UpdateUser
from examples.api_for_sqlalchemy.models import User
from examples.api_for_sqlalchemy.models.schemas import UserPatchSchema, UserSchema
from examples.api_for_sqlalchemy.models.schemas.user import UserInSchema
from fastapi_jsonapi import SqlalchemyEngine
from fastapi_jsonapi.exceptions import (
    BadRequest,
    HTTPException,
)
from fastapi_jsonapi.misc.sqla.factories.meta_base import FactoryUseMode
from fastapi_jsonapi.misc.sqla.generics.base import DetailViewBaseGeneric, ListViewBaseGeneric
from fastapi_jsonapi.misc.sqla.updaters.exceptions import ObjectNotFound
from fastapi_jsonapi.querystring import QueryStringManager
from fastapi_jsonapi.schema import JSONAPIResultDetailSchema


class UserDetail(DetailViewBaseGeneric):
    session_dependency = Depends(Connector.get_session)

    @classmethod
    async def patch(
        cls,
        obj_id,
        data: UserPatchSchema,
        query_params: QueryStringManager,
        session: AsyncSession = session_dependency,
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
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ex.description)

        user = UserSchema.from_orm(user_obj)
        return user


class UserList(ListViewBaseGeneric):
    session_dependency = Depends(Connector.get_session)

    async def post(
        self,
        data: UserInSchema,
        query_params: QueryStringManager,
        session: AsyncSession = session_dependency,
    ) -> JSONAPIResultDetailSchema:
        user_obj: User = await UserFactory.create_object_generic(
            data_as_schema=data,
            query_params=query_params,
            session=session,
            exc=ErrorCreateUserObject,
            factory_mode=FactoryUseMode.production,
        )
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
