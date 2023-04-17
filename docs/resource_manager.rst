.. _resource_manager:

Resource Manager
================

.. currentmodule:: fastapi_jsonapi

Resource manager is the link between your logical data abstraction, your data layer and optionally other software. It is the place where logic management of your resource is located.

FastAPI-JSONAPI provides three kinds of resource managers with default methods implemented according to the JSON:API 1.0 specification:

* **ResourceList**: provides get and post methods to retrieve or create a collection of objects.
* **ResourceDetail**: provides get, patch and delete methods to retrieve details of an object, update or delete it
* **ResourceRelationship**: provides get, post, patch and delete methods to get, create, update and delete relationships between objects. **IN DEVELOPING**

You can rewrite each default method implementation to customize it. If you rewrite all default methods of a resource manager or if you rewrite a method and disable access to others, you don't have to set any attributes of your resource manager.

All url are pased via helper class **QueryStringManager**, which make parsing url query string according json-api. If you want override implementation class used you can do it for 1 resource via attribute.
    :qs_manager_class: default implementation via  **QueryStringManager**

or globally via:
.. code-block::python

    api = Api(blueprint=api_blueprint, qs_manager_class=CustomQS)

Required attributes
-------------------

If you want to use one of the resource manager default method implementations you have to set two required attributes in your resource manager: schema and data_layer.

    :schema: the logical data abstraction used by the resource manager. It must be a class inherited from marshmallow_jsonapi.schema.Schema.
    :data_layer: data layer information used to initialize your data layer (If you want to learn more: :ref:`data_layer`)

ResourceList
--------------

Example:

.. code-block:: python

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



ResourceDetail
--------------

Example:

.. code-block:: python

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

This minimal ResourceDetail configuration provides a GET, PATCH and DELETE interface to retrieve details of an object, update and delete it with all-powerful features like sparse fieldsets and including related objects.

If your schema has relationship fields you can update an object and also update its links to (one or more) related objects at the same time. For an example see :ref:`quickstart`.
