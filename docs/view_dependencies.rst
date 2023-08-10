.. _view_dependencies:

ViewDependencies
================

.. currentmodule:: fastapi_jsonapi

As you already know, in the process of its work, FastAPI-JSONAPI interacts between application layers.
Sometimes there are things that are necessary to process requests but are only computable at runtime.
In order for ResourceManager and DataLayer to use such things, there is a mechanism called **method_dependencies**.

The most common cases of such things are database session and access handling.
The example below demonstrates some simple implementation of these ideas using sqlalchemy.

Example:

.. code-block:: python

    from typing import Dict, Optional

    from fastapi import Depends, Header
    from pydantic import BaseModel
    from sqlalchemy.engine import make_url
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.orm import sessionmaker
    from typing_extensions import Annotated

    from fastapi_jsonapi.exceptions import Forbidden
    from fastapi_jsonapi.misc.sqla.generics.base import (
        DetailViewBaseGeneric,
        ListViewBaseGeneric,
    )
    from fastapi_jsonapi.views.utils import (
        HTTPMethod,
        HTTPMethodConfig,
    )
    from fastapi_jsonapi.views.view_base import ViewBase


    def get_async_sessionmaker() -> sessionmaker:
        _async_session = sessionmaker(
            bind=create_async_engine(
                url=make_url(
                    f"sqlite+aiosqlite:///tmp/db.sqlite3",
                )
            ),
            class_=AsyncSession,
            expire_on_commit=False,
        )
        return _async_session


    async def async_session_dependency():
        """
        Get session as dependency

        :return:
        """
        session_maker = get_async_sessionmaker()
        async with session_maker() as db_session:  # type: AsyncSession
            yield db_session
            await db_session.rollback()


    class SessionDependency(BaseModel):
        session: AsyncSession = Depends(async_session_dependency)

        class Config:
            arbitrary_types_allowed = True


    async def common_handler(view: ViewBase, dto: BaseModel) -> Dict:
        return {"session": dto.session}


    async def check_that_user_is_admin(x_auth: Annotated[str, Header()]):
        if x_auth != "admin":
            raise Forbidden(detail="Only admin user have permissions to this endpoint")


    class AdminOnlyPermission(BaseModel):
        is_admin: Optional[bool] = Depends(check_that_user_is_admin)


    class DetailView(DetailViewBaseGeneric):
        method_dependencies: Dict[HTTPMethod, HTTPMethodConfig] = {
            HTTPMethod.ALL: HTTPMethodConfig(
                dependencies=SessionDependency,
                prepare_data_layer_kwargs=common_handler,
            ),
        }


    class ListView(ListViewBaseGeneric):
        method_dependencies: Dict[HTTPMethod, HTTPMethodConfig] = {
            HTTPMethod.GET: HTTPMethodConfig(dependencies=AdminOnlyPermission),
            HTTPMethod.ALL: HTTPMethodConfig(
                dependencies=SessionDependency,
                prepare_data_layer_kwargs=common_handler,
            ),
        }


In this example, the focus should be on the **HTTPMethod** and **HTTPMethodConfig** entities.
By setting the **method_dependencies** attribute, you can set FastAPI dependencies for endpoints,
as well as manage the creation of additional kwargs needed to initialize the DataLayer.

Dependencies can be any Pydantic model containing Depends as default values.
It's really the same as if you defined the dependency session for the endpoint as:

.. code-block:: python

    from fastapi import FastAPI, Depends
    from sqlalchemy.ext.asyncio import AsyncSession

    app = FastAPI()


    @app.get("/items")
    def get_items(session: AsyncSession = Depends(async_session_dependency)):
        pass


Dependencies do not have to be used to generate DataLayer keys and can be used for any purpose,
as is the case with the **check_that_user_is_admin** function, which is used to check permissions.
In case the header "X-AUTH" is not equal to "admin", the Forbidden response will be returned.

In this case, if you do not set the "X-AUTH" header, it will work like this

Request:

.. literalinclude:: ./http_snippets/snippets/view_dependencies__get_items_forbidden
  :language: HTTP


Response:

.. literalinclude:: ./http_snippets/snippets/view_dependencies__get_items_forbidden_result
  :language: HTTP


and when X-AUTH is set, it will work like this

Request:

.. literalinclude:: ./http_snippets/snippets/view_dependencies__get_items_with_permissions
  :language: HTTP


Response:

.. literalinclude:: ./http_snippets/snippets/view_dependencies__get_items_with_permissions_result
  :language: HTTP


Handlers
--------

As noted above, dependencies can be used to create a kwargs for a DataLayer.
To do this, you need to define **prepare_data_layer_kwargs** in **HTTPMethodConfig**.
This is a callable object which can be synchronous or asynchronous.

Its signature should look like this

.. code-block:: python

    async def my_handler(view: ViewBase, dto: BaseModel) -> Dict[str, Any]:
        pass

or this

.. code-block:: python

    async def my_handler(view: ViewBase) -> Dict[str, Any]:
        pass


In the case of dto, it is an instance of the class corresponds to what
is in **HTTPMethodConfig.dependencies** and should only be present in the function
signature if dependencies is not None.

The **HTTPMethodConfig.ALL** method has special behavior. When declared,
its dependencies will be passed to each endpoint regardless of the existence of other configs.

Explaining with a specific example, in the case when **HTTPMethod.ALL** is declared and
it has dependencies, and also a method such as **HTTPMethod.GET** also has dependencies,
the signature for the **HTTPMethod.GET** handler will be a union of dependencies

Example:

.. code-block:: python

    from typing import Dict

    from fastapi import Depends
    from pydantic import BaseModel

    from fastapi_jsonapi.misc.sqla.generics.base import DetailViewBaseGeneric
    from fastapi_jsonapi.views.utils import HTTPMethod, HTTPMethodConfig
    from fastapi_jsonapi.views.view_base import ViewBase


    def one():
        return 1


    def two():
        return 2


    class CommonDependency(BaseModel):
        key_1: int = Depends(one)


    class GetDependency(BaseModel):
        key_2: int = Depends(two)


    class DependencyMix(CommonDependency, GetDependency):
        pass


    def common_handler(view: ViewBase, dto: CommonDependency) -> Dict:
        return {"key_1": dto.key_1}


    def get_handler(view: ViewBase, dto: DependencyMix):
        return {"key_2": dto.key_2}


    class DetailView(DetailViewBaseGeneric):
        method_dependencies = {
            HTTPMethod.ALL: HTTPMethodConfig(
                dependencies=CommonDependency,
                prepare_data_layer_kwargs=common_handler,
            ),
            HTTPMethod.GET: HTTPMethodConfig(
                dependencies=GetDependency,
                prepare_data_layer_kwargs=get_handler,
            ),
        }


In this case DataLayer.__init__ will get ``{"key_1": 1, "key_2": 2}`` as kwargs.

You can take advantage of this knowledge and do something with the ``key_1`` value,
because before entering the DataLayer, the results of both handlers are defined as:

.. code-block:: python

    dl_kwargs = common_handler(view, dto)
    dl_kwargs.update(get_handler(view, dto))

You can override the value of ``key_1`` in the handler

.. code-block:: python

    def get_handler(view: ViewBase, dto: DependencyMix):
        return {"key_1": 42, "key_2": dto.key_2}

or just overriding the dependency

.. code-block:: python

    def handler(view, dto):
        return 42

    class GetDependency(BaseModel):
        key_1: int = Depends(handler)
        key_2: int = Depends(two)

In both cases DataLayer.__init__ will get ``{"key_1": 42, "key_2": 2}`` as kwargs
