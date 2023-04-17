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
import sys
from pathlib import Path
from typing import Any, Dict, List, Union, Optional

import uvicorn
from fastapi import APIRouter, Depends, FastAPI
from pydantic import BaseModel
from sqlalchemy import Column, Text, Integer, select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import Select

from fastapi_jsonapi import RoutersJSONAPI
from fastapi_jsonapi import SqlalchemyEngine
from fastapi_jsonapi.data_layers.orm import DBORMType
from fastapi_jsonapi.openapi import custom_openapi
from fastapi_jsonapi.querystring import QueryStringManager
from fastapi_jsonapi.schema import JSONAPIResultListSchema
from fastapi_jsonapi.schema import collect_app_orm_schemas

CURRENT_FILE = Path(__file__).resolve()
CURRENT_DIR = CURRENT_FILE.parent
PROJECT_DIR = CURRENT_DIR.parent.parent

sys.path.append(str(PROJECT_DIR))

Base = declarative_base()


def async_session() -> sessionmaker:
    uri = "sqlite+aiosqlite:///db.sqlite3"
    engine = create_async_engine(url=make_url(uri))
    _async_session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    return _async_session


class Connector:

    @classmethod
    async def get_session(cls):
        """
        Getting a session to the database.

        :return:
        """
        async_session_ = async_session()
        async with async_session_() as db_session:
            async with db_session.begin():
                yield db_session


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    first_name: str = Column(Text, nullable=True)


class UserBaseSchema(BaseModel):
    """User base schema."""

    class Config:
        """Pydantic schema config."""
        orm_mode = True

    first_name: Optional[str] = None


class UserPatchSchema(UserBaseSchema):
    """User PATCH schema."""


class UserInSchema(UserBaseSchema):
    """User input schema."""


class UserSchema(UserInSchema):
    """User item schema."""

    class Config:
        """Pydantic model config."""
        orm_mode = True
        model = "users"

    id: int


class UserDetail:

    @classmethod
    async def get(cls, obj_id: int, session: AsyncSession = Depends(Connector.get_session)) -> UserSchema:
        user: User = (await session.execute(select(User).where(User.id == obj_id))).scalar_one()
        return UserSchema.from_orm(user)

    @classmethod
    async def patch(cls, obj_id: int, data: UserPatchSchema, session: AsyncSession = Depends(Connector.get_session)) -> UserSchema:
        user: User = (await session.execute(select(User).where(User.id == obj_id))).scalar_one()
        user.first_name = data.first_name
        await session.commit()
        return UserSchema.from_orm(user)

    @classmethod
    async def delete(cls, obj_id: int, session: AsyncSession = Depends(Connector.get_session)) -> None:
        user: User = (await session.execute(select(User).where(User.id == obj_id))).scalar_one()
        await session.delete(user)
        await session.commit()


class UserList:
    @classmethod
    async def get(
            cls, query_params: QueryStringManager, session: AsyncSession = Depends(Connector.get_session)
    ) -> Union[Select, JSONAPIResultListSchema]:
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
    async def post(cls, data: UserInSchema, session: AsyncSession = Depends(Connector.get_session)) -> UserSchema:
        user = User(first_name=data.first_name)
        session.add(user)
        await session.commit()
        return UserSchema.from_orm(user)


def add_routes(app: FastAPI) -> List[Dict[str, Any]]:
    tags = [
        {
            "name": "User",
            "description": "",
        },
    ]

    routers: APIRouter = APIRouter()
    RoutersJSONAPI(
        routers=routers,
        path="/user",
        tags=["User"],
        class_detail=UserDetail,
        class_list=UserList,
        schema=UserSchema,
        type_resource="user",
        schema_in_patch=UserPatchSchema,
        schema_in_post=UserInSchema,
        model=User,
        engine=DBORMType.sqlalchemy,
    )

    app.include_router(routers, prefix="")
    return tags


async def sqlalchemy_init() -> None:
    uri = "sqlite+aiosqlite:///db.sqlite3"
    engine = create_async_engine(url=make_url(uri))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


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
    custom_openapi(app, title="API for SQLAlchemy")
    collect_app_orm_schemas(app)
    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "test:app",
        host="0.0.0.0",
        port=8084,
        reload=True,
        app_dir=str(CURRENT_DIR),
    )

```

This example provides the following API structure:

| URL               | method | endpoint      | Usage                     |
|-------------------|--------|---------------|---------------------------|
| /user             | GET    | user_list     | Get a collection of users |
| /user             | POST   | user_list     | Create a user             |
| /user/< int:int > | GET    | user_detail   | Get user details          |
| /user/< int:int > | PATCH  | person_detail | Update a user             |
| /user/< int:int > | DELETE | person_detail | Delete a user             |
