.. _data_layer:

Data layer
==========

.. currentmodule:: fastapi_jsonapi

| The data layer is a CRUD interface between resource manager and data. It is a very flexible system to use any ORM or data storage. You can even create a data layer that uses multiple ORMs and data storage to manage your own objects. The data layer implements a CRUD interface for objects and relationships. It also manages pagination, filtering and sorting.
|
| FastAPI-JSONAPI has a full-featured data layer that uses the popular ORM `SQLAlchemy <https://www.sqlalchemy.org/>`_.

.. note::

    The default data layer used by a resource manager is the SQLAlchemy one. So if that's what you want to use, you don't have to specify the class of the data layer in the resource manager

To configure the data layer you have to set its required parameters in the resource manager.

Example:

.. code-block:: python

    from http import HTTPStatus
    from typing import (
        List,
        Union,
    )

    from fastapi import Depends
    from sqlalchemy import select, desc
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.sql import Select
    from tortoise.exceptions import DoesNotExist

    from examples.api_for_sqlalchemy.extensions.sqlalchemy import Connector
    from examples.api_for_sqlalchemy.helpers.factories.meta_base import FactoryUseMode
    from examples.api_for_sqlalchemy.helpers.factories.user import UserFactory, ErrorCreateUserObject
    from examples.api_for_sqlalchemy.helpers.updaters.exceptions import ObjectNotFound
    from examples.api_for_sqlalchemy.helpers.updaters.update_user import UpdateUser, ErrorUpdateUserObject
    from examples.api_for_sqlalchemy.models.pydantic import UserSchema, UserPatchSchema
    from examples.api_for_sqlalchemy.models.pydantic.user import UserInSchema
    from examples.api_for_sqlalchemy.models.sqlalchemy import User
    from fastapi_jsonapi import SqlalchemyEngine
    from fastapi_jsonapi.exceptions import (
        BadRequest,
        HTTPException,
    )
    from fastapi_jsonapi.querystring import QueryStringManager
    from fastapi_jsonapi.schema import JSONAPIResultListSchema


    class UserDetail:
        @classmethod
        async def get_user(cls, user_id, query_params: QueryStringManager, session: AsyncSession) -> User:
            """
            Get user by id from ORM.

            :param user_id: int
            :param query_params: QueryStringManager
            :return: User model.
            :raises HTTPException: if user not found.
            """
            user: User
            try:
                user = (await session.execute(select(User).where(User.id == user_id))).scalar_one()
            except DoesNotExist:
                raise HTTPException(
                    status_code=HTTPStatus.FORBIDDEN,
                    detail="User with id {id} not found".format(id=user_id),
                )

            return user

        @classmethod
        async def get(cls, obj_id, query_params: QueryStringManager, session: AsyncSession = Depends(Connector.get_session)) -> UserSchema:
            user: User = await cls.get_user(user_id=obj_id, query_params=query_params, session=session)
            return UserSchema.from_orm(user)

        @classmethod
        async def patch(cls, obj_id, data: UserPatchSchema, query_params: QueryStringManager, session: AsyncSession = Depends(Connector.get_session)) -> UserSchema:
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


    class UserList:
        @classmethod
        async def get(cls, query_params: QueryStringManager, session: AsyncSession = Depends(Connector.get_session)) -> Union[Select, JSONAPIResultListSchema]:
            user_query = select(User)
            dl = SqlalchemyEngine(query=user_query, schema=UserSchema, model=User, session=session)
            count, users_db = await dl.get_collection(qs=query_params)
            total_pages = count // query_params.pagination.size + (count % query_params.pagination.size and 1)
            users: List[UserSchema] = [UserSchema.from_orm(i_user) for i_user in users_db]
            return JSONAPIResultListSchema(
                meta={"count": count, "totalPages": total_pages},
                data=[{"id": i_obj.id, "attributes": i_obj.dict(), "type": "user"} for i_obj in users],
            )

        @classmethod
        async def post(cls, data: UserInSchema, query_params: QueryStringManager, session: AsyncSession = Depends(Connector.get_session)) -> UserSchema:
            try:
                user_obj = await UserFactory.create(
                    data=data.dict(),
                    mode=FactoryUseMode.production,
                    header=query_params.headers,
                    session=session,
                )
            except ErrorCreateUserObject as ex:
                raise BadRequest(ex.description, ex.field)

            user = UserSchema.from_orm(user_obj)
            return user

