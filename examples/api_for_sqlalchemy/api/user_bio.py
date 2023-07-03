from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from examples.api_for_sqlalchemy.extensions.sqlalchemy import Connector
from examples.api_for_sqlalchemy.helpers.factories.user_bio import ErrorCreateUserBioObject, UserBioFactory
from examples.api_for_sqlalchemy.models import UserBio
from examples.api_for_sqlalchemy.models.schemas.user_bio import UserBioInSchema
from fastapi_jsonapi import SqlalchemyEngine
from fastapi_jsonapi.misc.sqla.factories.meta_base import FactoryUseMode
from fastapi_jsonapi.misc.sqla.generics.base import DetailViewBaseGeneric, ListViewBaseGeneric
from fastapi_jsonapi.querystring import QueryStringManager
from fastapi_jsonapi.schema import JSONAPIResultDetailSchema


class UserBioDetail(DetailViewBaseGeneric):
    session_dependency = Depends(Connector.get_session)


class UserBioList(ListViewBaseGeneric):
    session_dependency = Depends(Connector.get_session)

    async def post(
        self,
        data: UserBioInSchema,
        query_params: QueryStringManager,
        session: AsyncSession = session_dependency,
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
