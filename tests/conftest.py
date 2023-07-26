import asyncio
import logging

import pytest
from fastapi import APIRouter, FastAPI
from httpx import AsyncClient
from pytest import fixture  # noqa PT013
from pytest_asyncio import fixture as async_fixture
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from fastapi_jsonapi import RoutersJSONAPI
from fastapi_jsonapi.exceptions.handlers import register_exception_handlers
from tests.fixtures.entities import (  # noqa
    child_1,
    child_2,
    child_3,
    child_4,
    computer_1,
    computer_2,
    p1_c1_association,
    p1_c2_association,
    p2_c1_association,
    p2_c2_association,
    p2_c3_association,
    parent_1,
    parent_2,
    parent_3,
    user_1,
    user_1_bio,
    user_1_comments_for_u2_posts,
    user_1_post_for_comments,
    user_1_posts,
    user_2,
    user_2_comment_for_one_u1_post,
    user_2_posts,
)
from tests.fixtures.views import (  # noqa
    child_detail_view,
    child_list_view,
    computer_detail_view,
    computer_list_view,
    detail_view_base_generic,
    list_view_base_generic,
    list_view_base_generic_helper_for_sqla,
    parent_detail_view,
    parent_list_view,
    post_detail_view,
    post_list_view,
    user_bio_detail_view,
    user_bio_list_view,
    user_detail_view,
    user_list_view,
)
from tests.models import (
    Base,
    Child,
    Computer,
    Parent,
    Post,
    User,
    UserBio,
)
from tests.schemas import (
    ChildInSchema,
    ChildPatchSchema,
    ChildSchema,
    ComputerInSchema,
    ComputerPatchSchema,
    ComputerSchema,
    ParentPatchSchema,
    ParentSchema,
    PostInSchema,
    PostPatchSchema,
    PostSchema,
    UserBioSchema,
    UserInSchema,
    UserPatchSchema,
    UserSchema,
)


def init_tests():
    # configure_logging()
    logging.getLogger("faker.factory").setLevel(logging.INFO)


init_tests()


@pytest.fixture(scope="session")
def event_loop():
    """
    Create an instance of the default event loop for each test case.

    Why:
    https://stackoverflow.com/questions/66054356/multiple-async-unit-tests-fail-but-running-them-one-by-one-will-pass
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@fixture(scope="session")
def sqla_uri():
    return "sqlite+aiosqlite:///tests/db.sqlite3"
    # return "sqlite+aiosqlite:///:memory:"


# DB connections ⬇️


@async_fixture(scope="class")
async def async_engine(sqla_uri):
    engine = create_async_engine(url=make_url(sqla_uri))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    return engine


@async_fixture(scope="class")
async def async_session_plain(async_engine):
    session = sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return session


@async_fixture(scope="class")
async def async_session(async_session_plain):
    async with async_session_plain() as session:
        yield session
        # async with session.begin():


@fixture(scope="class")
def async_session_dependency(async_session_plain):
    async def get_session():
        """

        :return:
        """
        async with async_session_plain() as db_session:
            yield db_session

    return get_session


@fixture()
def app_max_include_depth():
    return 5


@fixture()
def app_plain(app_max_include_depth) -> FastAPI:
    app = FastAPI(
        title="FastAPI and SQLAlchemy",
        debug=True,
        openapi_url="/openapi.json",
        docs_url="/docs",
    )
    app.config = {"MAX_INCLUDE_DEPTH": app_max_include_depth}
    return app


# Routing ⬇️


@fixture()
def app(
    app_plain: FastAPI,
    user_detail_view,  # noqa F811
    user_list_view,  # noqa F811
    user_bio_detail_view,  # noqa F811
    user_bio_list_view,  # noqa F811
    post_detail_view,  # noqa F811
    post_list_view,  # noqa F811
    parent_detail_view,  # noqa F811
    parent_list_view,  # noqa F811
    child_detail_view,  # noqa F811
    child_list_view,  # noqa F811
    computer_detail_view,  # noqa F811
    computer_list_view,  # noqa F811
):
    router: APIRouter = APIRouter()
    RoutersJSONAPI(
        router=router,
        path="/users",
        tags=["User"],
        class_detail=user_detail_view,
        class_list=user_list_view,
        schema=UserSchema,
        resource_type="user",
        schema_in_patch=UserPatchSchema,
        schema_in_post=UserInSchema,
        model=User,
    )

    RoutersJSONAPI(
        router=router,
        path="/posts",
        tags=["Post"],
        class_detail=post_detail_view,
        class_list=post_list_view,
        schema=PostSchema,
        resource_type="post",
        schema_in_patch=PostPatchSchema,
        schema_in_post=PostInSchema,
        model=Post,
    )

    RoutersJSONAPI(
        router=router,
        path="/user-bio",
        tags=["Bio"],
        class_detail=user_bio_detail_view,
        class_list=user_bio_list_view,
        schema=UserBioSchema,
        resource_type="user_bio",
        model=UserBio,
    )

    RoutersJSONAPI(
        router=router,
        path="/parents",
        tags=["Parent"],
        class_detail=parent_detail_view,
        class_list=parent_list_view,
        schema=ParentSchema,
        resource_type="parent",
        schema_in_patch=ParentPatchSchema,
        schema_in_post=ParentPatchSchema,
        model=Parent,
    )

    RoutersJSONAPI(
        router=router,
        path="/children",
        tags=["Child"],
        class_detail=child_detail_view,
        class_list=child_list_view,
        schema=ChildSchema,
        resource_type="child",
        schema_in_patch=ChildPatchSchema,
        schema_in_post=ChildInSchema,
        model=Child,
    )
    RoutersJSONAPI(
        router=router,
        path="/computers",
        tags=["Computer"],
        class_detail=computer_detail_view,
        class_list=computer_list_view,
        model=Computer,
        schema=ComputerSchema,
        resource_type="computer",
        schema_in_patch=ComputerPatchSchema,
        schema_in_post=ComputerInSchema,
    )

    app_plain.include_router(router, prefix="")
    register_exception_handlers(app_plain)

    return app_plain


@async_fixture()
async def client(app: FastAPI) -> AsyncClient:
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
