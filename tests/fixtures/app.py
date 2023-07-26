from pathlib import Path

import uvicorn
from fastapi import APIRouter, FastAPI
from pytest import fixture  # noqa PT013

from fastapi_jsonapi import RoutersJSONAPI
from fastapi_jsonapi.exceptions.handlers import register_exception_handlers
from tests.fixtures.views import (
    DetailViewBaseGeneric,
    ListViewBaseGeneric,
)
from tests.models import (
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

CURRENT_FILE = Path(__file__).resolve()
CURRENT_DIR = CURRENT_FILE.parent

MAX_INCLUDE_DEPTH = 5


def build_app_plain() -> FastAPI:
    app = FastAPI(
        title="FastAPI and SQLAlchemy",
        debug=True,
        openapi_url="/openapi.json",
        docs_url="/docs",
    )
    app.config = {"MAX_INCLUDE_DEPTH": MAX_INCLUDE_DEPTH}

    return app


def add_routers(app_plain: FastAPI):
    router: APIRouter = APIRouter()
    RoutersJSONAPI(
        router=router,
        path="/users",
        tags=["User"],
        class_detail=DetailViewBaseGeneric,
        class_list=ListViewBaseGeneric,
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
        class_detail=DetailViewBaseGeneric,
        class_list=ListViewBaseGeneric,
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
        class_detail=DetailViewBaseGeneric,
        class_list=ListViewBaseGeneric,
        schema=UserBioSchema,
        resource_type="user_bio",
        model=UserBio,
    )

    RoutersJSONAPI(
        router=router,
        path="/parents",
        tags=["Parent"],
        class_detail=DetailViewBaseGeneric,
        class_list=ListViewBaseGeneric,
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
        class_detail=DetailViewBaseGeneric,
        class_list=ListViewBaseGeneric,
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
        class_detail=DetailViewBaseGeneric,
        class_list=ListViewBaseGeneric,
        model=Computer,
        schema=ComputerSchema,
        resource_type="computer",
        schema_in_patch=ComputerPatchSchema,
        schema_in_post=ComputerInSchema,
    )

    app_plain.include_router(router, prefix="")
    register_exception_handlers(app_plain)

    return app_plain


@fixture()
def app_plain() -> FastAPI:
    return build_app_plain()


@fixture()
def app(app_plain: FastAPI):
    add_routers(app_plain)

    return app_plain


if __name__ == "__main__":
    fastapi_app = build_app_plain()
    add_routers(fastapi_app)
    uvicorn.run(
        "asgi:app",
        host="0.0.0.0",
        port=8082,
        reload=True,
        app_dir=str(CURRENT_DIR),
    )
