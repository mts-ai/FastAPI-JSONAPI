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
from examples.api_for_tortoise_orm.models.pydantic import UserSchema, UserPatchJSONAPISchema, UserJSONAPIListSchema, \
    UserPostJSONAPISchema
from examples.api_for_tortoise_orm.models.tortoise import User
from fastapi_rest_jsonapi import json_api_pagination

from fastapi_rest_jsonapi.exceptions import (
    BadRequest,
    HTTPException,
)
from fastapi_rest_jsonapi.filter import json_api_filter
from fastapi_rest_jsonapi.querystring import QueryStringManager


class UserDetail(object):
    @classmethod
    async def get_user(cls, user_id, query_params: QueryStringManager) -> User:
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
    async def get(cls, obj_id, query_params: QueryStringManager) -> UserSchema:
        user: User = await cls.get_user(user_id=obj_id, query_params=query_params)
        return UserSchema.from_orm(user)

    @classmethod
    async def patch(cls, obj_id, data: UserPatchJSONAPISchema, query_params: QueryStringManager) -> UserSchema:
        user_obj: User
        try:
            user_obj = await UpdateUser.update(
                obj_id,
                data.attributes.dict(exclude_unset=True),
                query_params.headers,
            )
        except ErrorUpdateUserObject as ex:
            raise BadRequest(ex.description, ex.field)
        except ObjectNotFound as ex:
            raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=ex.description)

        device = UserSchema.from_orm(user_obj)
        return device


class UserList(object):
    @classmethod
    async def get(cls, query_params: QueryStringManager) -> Union[QuerySet, UserJSONAPIListSchema]:
        extended_fields: List[str] = query_params.fields.get("users", [])
        if not extended_fields:
            device_query = User.filter().order_by("-id")
            return await json_api_filter(query=device_query, schema=UserSchema, query_params=query_params)

        user_query = User.filter().order_by("-id")
        query: QuerySet = await json_api_filter(query=user_query, schema=UserSchema, query_params=query_params)
        query, total_pages, count = await json_api_pagination(query=query, query_params=query_params)
        users_db: List[User] = await query.all()
        users: List[UserSchema] = [UserSchema.from_orm(i_user) for i_user in users_db]

        return UserJSONAPIListSchema(
            meta={"count": count, "totalPages": total_pages},
            data=[{"id": i_obj.id, "type": "Device", "attributes": i_obj.dict()} for i_obj in users],
        )

    @classmethod
    async def post(cls, data: UserPostJSONAPISchema, query_params: QueryStringManager) -> UserSchema:
        try:
            device_obj = await UserFactory.create(
                data=data.attributes.dict(),
                mode=FactoryUseMode.production,
                header=query_params.headers,
            )
        except ErrorCreateUserObject as ex:
            raise BadRequest(ex.description, ex.field)

        user = UserSchema.from_orm(device_obj)
        return user
