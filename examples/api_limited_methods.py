import sys
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
PROJECT_DIR = CURRENT_DIR.parent.parent
DB_URL = f"sqlite+aiosqlite:///{CURRENT_DIR}/db.sqlite3"
sys.path.append(str(PROJECT_DIR))

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=True)


class UserAttributesBaseSchema(BaseModel):
    name: str

    class Config:
        orm_mode = True


class UserSchema(UserAttributesBaseSchema):
    """User base schema."""


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
    method_dependencies: ClassVar = {
        HTTPMethod.ALL: HTTPMethodConfig(
            dependencies=SessionDependency,
            prepare_data_layer_kwargs=session_dependency_handler,
        ),
    }


class UserListView(ListViewBaseGeneric):
    method_dependencies: ClassVar = {
        HTTPMethod.ALL: HTTPMethodConfig(
            dependencies=SessionDependency,
            prepare_data_layer_kwargs=session_dependency_handler,
        ),
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
        model=User,
        resource_type="user",
        methods=[
            RoutersJSONAPI.Methods.GET_LIST,
            RoutersJSONAPI.Methods.POST,
            RoutersJSONAPI.Methods.GET,
        ],
    )

    app.include_router(router, prefix="")
    return tags


def create_app() -> FastAPI:
    """
    Create app factory.

    :return: app
    """
    app = FastAPI(
        title="FastAPI app with limited methods",
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
        app,
        host="0.0.0.0",
        port=8080,
    )
