from http import HTTPStatus
from typing import (
    List,
    Union,
)

from tortoise.exceptions import DoesNotExist
from tortoise.queryset import QuerySet

from examples.api_for_tortoise_orm.helpers.factories.meta_base import FactoryUseMode
from examples.api_for_tortoise_orm.helpers.factories.user import UserFactory, ErrorCreateUserObject
from examples.api_for_tortoise_orm.helpers.updaters.exceptions import ObjectNotFound
from examples.api_for_tortoise_orm.helpers.updaters.update_user import UpdateUser, ErrorUpdateUserObject
from examples.api_for_tortoise_orm.models.pydantic import UserSchema, UserPatchSchema
from examples.api_for_tortoise_orm.models.pydantic.user import UserInSchema
from examples.api_for_tortoise_orm.models.tortoise import User
from fastapi_jsonapi.data_layers.tortoise_orm import TortoiseDataLayer
from fastapi_jsonapi.exceptions import (
    BadRequest,
    HTTPException,
)
from fastapi_jsonapi.querystring import QueryStringManager
from fastapi_jsonapi.schema import JSONAPIResultListSchema


class UserDetail:
    @classmethod
    async def get_user(cls, user_id: int, query_params: QueryStringManager) -> User:
        """
        Get user by id from ORM.

        :param user_id: int
        :param query_params: QueryStringManager
        :return: User model.
        :raises HTTPException: if user not found.
        """
        user: User
        try:
            user = await User.get(id=user_id)
        except DoesNotExist:
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail="User with id {id} not found".format(id=user_id),
            )

        return user

    @classmethod
    async def get(cls, obj_id: int, query_params: QueryStringManager) -> UserSchema:
        user: User = await cls.get_user(user_id=obj_id, query_params=query_params)
        return UserSchema.from_orm(user)

    @classmethod
    async def patch(cls, obj_id: int, data: UserPatchSchema, query_params: QueryStringManager) -> UserSchema:
        user_obj: User
        try:
            user_obj = await UpdateUser.update(
                obj_id,
                data.dict(exclude_unset=True),
                query_params.headers,
            )
        except ErrorUpdateUserObject as ex:
            raise BadRequest(ex.description, ex.field)
        except ObjectNotFound as ex:
            raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=ex.description)

        user = UserSchema.from_orm(user_obj)
        return user


class UserList:
    @classmethod
    async def get(cls, query_params: QueryStringManager) -> Union[QuerySet, JSONAPIResultListSchema]:
        user_query = User.filter().order_by("-id")
        dl = TortoiseDataLayer(query=user_query, schema=UserSchema, model=User)
        count, users_db = await dl.get_collection(qs=query_params)
        total_pages = count // query_params.pagination.size + (count % query_params.pagination.size and 1)
        users: List[UserSchema] = [UserSchema.from_orm(i_user) for i_user in users_db]
        return JSONAPIResultListSchema(
            meta={"count": count, "totalPages": total_pages},
            data=[{"id": i_obj.id, "attributes": i_obj.dict(), "type": "user"} for i_obj in users],
        )

    @classmethod
    async def post(cls, data: UserInSchema, query_params: QueryStringManager) -> UserSchema:
        try:
            user_obj = await UserFactory.create(
                data=data.dict(),
                mode=FactoryUseMode.production,
                header=query_params.headers,
            )
        except ErrorCreateUserObject as ex:
            raise BadRequest(ex.description, ex.field)

        user = UserSchema.from_orm(user_obj)
        return user
