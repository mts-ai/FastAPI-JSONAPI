[![Last Commit](https://img.shields.io/github/last-commit/mts-ai/FastAPI-JSONAPI?style=for-the-badge)](https://github.com/mts-ai/FastAPI-JSONAPI)
[![PyPI](https://img.shields.io/pypi/v/fastapi-jsonapi?label=PyPI&style=for-the-badge)](https://pypi.org/project/FastAPI-JSONAPI/)
[![](https://img.shields.io/pypi/pyversions/FastAPI-JSONAPI?style=for-the-badge)](https://pypi.org/project/FastAPI-JSONAPI/)
[![](https://img.shields.io/github/license/ycd/manage-fastapi?style=for-the-badge)](https://pypi.org/project/FastAPI-JSONAPI/)
![GitHub Actions](https://img.shields.io/github/actions/workflow/status/mts-ai/FastAPI-JSONAPI/testing.yml?style=for-the-badge)
[![Read the Docs](https://img.shields.io/readthedocs/fastapi-jsonapi?style=for-the-badge)](https://fastapi-jsonapi.readthedocs.io/en/latest/)

[![📖 Docs (gh-pages)](https://github.com/mts-ai/FastAPI-JSONAPI/actions/workflows/documentation.yaml/badge.svg)](https://mts-ai.github.io/FastAPI-JSONAPI/)

# FastAPI-JSONAPI

FastAPI-JSONAPI is a FastAPI extension for building REST APIs.
Implementation of a strong specification [JSONAPI 1.0](http://jsonapi.org/).
This framework is designed to quickly build REST APIs and fit the complexity
of real life projects with legacy data and multiple data storages.

## Architecture

![docs/img/schema.png](docs/img/schema.png)

## Install

```bash
pip install FastAPI-JSONAPI
```

## A minimal API

Create a test.py file and copy the following code into it

```python
from pathlib import Path
from typing import Any, ClassVar, Dict

import uvicorn
from fastapi import APIRouter, Depends, FastAPI
from sqlalchemy import Column, Integer, Text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from fastapi_jsonapi import RoutersJSONAPI, init
from fastapi_jsonapi.misc.sqla.generics.base import DetailViewBaseGeneric, ListViewBaseGeneric
from fastapi_jsonapi.schema_base import BaseModel
from fastapi_jsonapi.views.utils import HTTPMethod, HTTPMethodConfig
from fastapi_jsonapi.views.view_base import ViewBase

CURRENT_FILE = Path(__file__).resolve()
CURRENT_DIR = CURRENT_FILE.parent
DB_URL = f"sqlite+aiosqlite:///{CURRENT_DIR}/db.sqlite3"

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=True)


class UserAttributesBaseSchema(BaseModel):
    name: str

    class Config:
        """Pydantic schema config."""

        orm_mode = True


class UserSchema(UserAttributesBaseSchema):
    """User base schema."""


class UserPatchSchema(UserAttributesBaseSchema):
    """User PATCH schema."""


class UserInSchema(UserAttributesBaseSchema):
    """User input schema."""


def async_session() -> sessionmaker:
    engine = create_async_engine(url=make_url(DB_URL))
    _async_session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    return _async_session


class Connector:
    @classmethod
    async def get_session(cls):
        """
        Get session as dependency

        :return:
        """
        sess = async_session()
        async with sess() as db_session:  # type: AsyncSession
            yield db_session
            await db_session.rollback()


async def sqlalchemy_init() -> None:
    engine = create_async_engine(url=make_url(DB_URL))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


class SessionDependency(BaseModel):
    session: AsyncSession = Depends(Connector.get_session)

    class Config:
        arbitrary_types_allowed = True


def session_dependency_handler(view: ViewBase, dto: SessionDependency) -> Dict[str, Any]:
    return {
        "session": dto.session,
    }


class UserDetailView(DetailViewBaseGeneric):
    method_dependencies: ClassVar[Dict[HTTPMethod, HTTPMethodConfig]] = {
        HTTPMethod.ALL: HTTPMethodConfig(
            dependencies=SessionDependency,
            prepare_data_layer_kwargs=session_dependency_handler,
        )
    }


class UserListView(ListViewBaseGeneric):
    method_dependencies: ClassVar[Dict[HTTPMethod, HTTPMethodConfig]] = {
        HTTPMethod.ALL: HTTPMethodConfig(
            dependencies=SessionDependency,
            prepare_data_layer_kwargs=session_dependency_handler,
        )
    }


def add_routes(app: FastAPI):
    tags = [
        {
            "name": "User",
            "description": "",
        },
    ]

    router: APIRouter = APIRouter()
    RoutersJSONAPI(
        router=router,
        path="/users",
        tags=["User"],
        class_detail=UserDetailView,
        class_list=UserListView,
        schema=UserSchema,
        resource_type="user",
        schema_in_patch=UserPatchSchema,
        schema_in_post=UserInSchema,
        model=User,
    )

    app.include_router(router, prefix="")
    return tags


def create_app() -> FastAPI:
    """
    Create app factory.

    :return: app
    """
    app = FastAPI(
        title="FastAPI and SQLAlchemy",
        debug=True,
        openapi_url="/openapi.json",
        docs_url="/docs",
    )
    add_routes(app)
    app.on_event("startup")(sqlalchemy_init)
    init(app)
    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        app_dir=str(CURRENT_DIR),
    )
```

This example provides the following API structure:

| URL               | method | endpoint    | Usage                     |
|-------------------|--------|-------------|---------------------------|
| `/users`          | GET    | user_list   | Get a collection of users |
| `/users`          | POST   | user_list   | Create a user             |
| `/users`          | DELETE | user_list   | Delete users              |
| `/users/{obj_id}` | GET    | user_detail | Get user details          |
| `/users/{obj_id}` | PATCH  | user_detail | Update a user             |
| `/users/{obj_id}` | DELETE | user_detail | Delete a user             |
