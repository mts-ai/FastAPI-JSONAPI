from fastapi import Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from examples.api_for_sqlalchemy.api.base import DetailViewBaseGeneric, ListViewBaseGeneric
from examples.api_for_sqlalchemy.extensions.sqlalchemy import Connector
from examples.api_for_sqlalchemy.helpers.factories.meta_base import FactoryUseMode
from examples.api_for_sqlalchemy.helpers.factories.post import ErrorCreatePostObject, PostFactory
from examples.api_for_sqlalchemy.models.schemas import (
    PostInSchema,
)
from fastapi_jsonapi import SqlalchemyEngine
from fastapi_jsonapi.exceptions import (
    BadRequest,
    HTTPException,
)
from fastapi_jsonapi.querystring import QueryStringManager
from fastapi_jsonapi.schema import JSONAPIResultDetailSchema


class PostDetail(DetailViewBaseGeneric):
    ...


class PostList(ListViewBaseGeneric):
    async def post(
        self,
        data: PostInSchema,
        query_params: QueryStringManager,
        session: AsyncSession = Depends(Connector.get_session),
    ) -> JSONAPIResultDetailSchema:
        try:
            post_obj = await PostFactory.create(
                data=data.dict(),
                mode=FactoryUseMode.production,
                header=query_params.headers,
                session=session,
            )
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                # detail=str(e),
            )
        except ErrorCreatePostObject as ex:
            raise BadRequest(ex.description, ex.field)

        dl = SqlalchemyEngine(
            schema=self.jsonapi.schema_detail,
            model=self.jsonapi.model,
            session=session,
        )
        view_kwargs = {"id": post_obj.id}
        return await self.get_detailed_result(
            dl=dl,
            view_kwargs=view_kwargs,
            query_params=query_params,
        )
