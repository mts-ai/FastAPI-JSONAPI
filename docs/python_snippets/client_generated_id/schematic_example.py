import sys
from pathlib import Path
from typing import ClassVar

import uvicorn
from fastapi import APIRouter, Depends, FastAPI
from fastapi_jsonapi.schema_base import Field, BaseModel as PydanticBaseModel
from sqlalchemy import Column, Integer, Text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from fastapi_jsonapi import RoutersJSONAPI, init
from fastapi_jsonapi.misc.sqla.generics.base import DetailViewBaseGeneric, ListViewBaseGeneric
from fastapi_jsonapi.views.utils import HTTPMethod, HTTPMethodConfig
from fastapi_jsonapi.views.view_base import ViewBase

CURRENT_FILE = Path(__file__).resolve()
CURRENT_DIR = CURRENT_FILE.parent
PROJECT_DIR = CURRENT_DIR.parent.parent
DB_URL = f"sqlite+aiosqlite:///{CURRENT_DIR.absolute()}/db.sqlite3"
sys.path.append(str(PROJECT_DIR))

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=False)
    name = Column(Text, nullable=True)


class BaseModel(PydanticBaseModel):
    class Config:
        orm_mode = True


class UserAttributesBaseSchema(BaseModel):
    name: str


class UserSchema(UserAttributesBaseSchema):
    """User base schema."""


class UserPatchSchema(UserAttributesBaseSchema):
    """User PATCH schema."""


class UserInSchema(UserAttributesBaseSchema):
    """User input schema."""

    id: int = Field(client_can_set_id=True)


async def get_session():
    sess = sessionmaker(
        bind=create_async_engine(url=make_url(DB_URL)),
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with sess() as db_session:  # type: AsyncSession
        yield db_session
        await db_session.rollback()


async def sqlalchemy_init() -> None:
    engine = create_async_engine(url=make_url(DB_URL))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


class SessionDependency(BaseModel):
    session: AsyncSession = Depends(get_session)

    class Config:
        arbitrary_types_allowed = True


def session_dependency_handler(view: ViewBase, dto: SessionDependency) -> dict:
    return {"session": dto.session}


class UserDetailView(DetailViewBaseGeneric):
    method_dependencies: ClassVar = {
        HTTPMethod.ALL: HTTPMethodConfig(
            dependencies=SessionDependency,
            prepare_data_layer_kwargs=session_dependency_handler,
        )
    }


class UserListView(ListViewBaseGeneric):
    method_dependencies: ClassVar = {
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
    current_file_name = CURRENT_FILE.name.replace(CURRENT_FILE.suffix, "")
    uvicorn.run(
        f"{current_file_name}:app",
        host="0.0.0.0",
        port=8084,
        reload=True,
        app_dir=str(CURRENT_DIR),
    )
