from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from fastapi import APIRouter, FastAPI
from pydantic import BaseModel, ConfigDict

from fastapi_jsonapi import RoutersJSONAPI, init
from fastapi_jsonapi.atomic import AtomicOperations
from tests.fixtures.views import (
    DetailViewBaseGeneric,
    ListViewBaseGeneric,
)
from tests.models import (
    Alpha,
    Beta,
    Child,
    Computer,
    CustomUUIDItem,
    Delta,
    Gamma,
    Parent,
    ParentToChildAssociation,
    Post,
    PostComment,
    Task,
    User,
    UserBio,
)
from tests.schemas import (
    AlphaSchema,
    BetaSchema,
    ChildInSchema,
    ChildPatchSchema,
    ChildSchema,
    ComputerInSchema,
    ComputerPatchSchema,
    ComputerSchema,
    CustomUUIDItemSchema,
    DeltaSchema,
    GammaSchema,
    ParentPatchSchema,
    ParentSchema,
    ParentToChildAssociationSchema,
    PostCommentSchema,
    PostInSchema,
    PostPatchSchema,
    PostSchema,
    TaskInSchema,
    TaskPatchSchema,
    TaskSchema,
    UserBioSchema,
    UserInSchema,
    UserPatchSchema,
    UserSchema,
)

from fastapi_jsonapi.data_typing import TypeModel
from fastapi_jsonapi.views.detail_view import DetailViewBase
from fastapi_jsonapi.views.list_view import ListViewBase

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
        path="/comments",
        tags=["Comment"],
        class_detail=DetailViewBaseGeneric,
        class_list=ListViewBaseGeneric,
        schema=PostCommentSchema,
        resource_type="post_comment",
        model=PostComment,
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
        path="/parent-to-child-association",
        tags=["Parent To Child Association"],
        class_detail=DetailViewBaseGeneric,
        class_list=ListViewBaseGeneric,
        schema=ParentToChildAssociationSchema,
        resource_type="parent-to-child-association",
        model=ParentToChildAssociation,
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

    RoutersJSONAPI(
        router=router,
        path="/tasks",
        tags=["Task"],
        class_detail=DetailViewBaseGeneric,
        class_list=ListViewBaseGeneric,
        model=Task,
        schema=TaskSchema,
        resource_type="task",
        schema_in_patch=TaskPatchSchema,
        schema_in_post=TaskInSchema,
    )

    RoutersJSONAPI(
        router=router,
        path="/custom-uuid-item",
        tags=["Custom UUID Item"],
        class_detail=DetailViewBaseGeneric,
        class_list=ListViewBaseGeneric,
        model=CustomUUIDItem,
        schema=CustomUUIDItemSchema,
        resource_type="custom_uuid_item",
    )

    atomic = AtomicOperations()

    app_plain.include_router(router, prefix="")
    app_plain.include_router(atomic.router, prefix="")

    init(app_plain)

    return app_plain


@pytest.fixture(scope="session")
def app_plain() -> FastAPI:
    return build_app_plain()


@pytest.fixture(scope="session")
def app(app_plain: FastAPI):
    add_routers(app_plain)

    return app_plain


def build_app_custom(
    model,
    schema,
    schema_in_patch=None,
    schema_in_post=None,
    path: str = "/misc",
    resource_type: str = "misc",
    class_list: type[ListViewBase] = ListViewBaseGeneric,
    class_detail: type[DetailViewBase] = DetailViewBaseGeneric,
) -> FastAPI:
    router: APIRouter = APIRouter()

    RoutersJSONAPI(
        router=router,
        path=path,
        tags=["Misc"],
        class_list=class_list,
        class_detail=class_detail,
        schema=schema,
        resource_type=resource_type,
        schema_in_patch=schema_in_patch,
        schema_in_post=schema_in_post,
        model=model,
    )

    app = build_app_plain()
    app.include_router(router, prefix="")

    atomic = AtomicOperations()
    app.include_router(atomic.router, prefix="")
    init(app)
    return app


def build_alphabet_app() -> FastAPI:
    return build_custom_app_by_schemas(
        [
            ResourceInfoDTO(
                path="/alpha",
                resource_type="alpha",
                model=Alpha,
                schema_=AlphaSchema,
            ),
            ResourceInfoDTO(
                path="/beta",
                resource_type="beta",
                model=Beta,
                schema_=BetaSchema,
            ),
            ResourceInfoDTO(
                path="/gamma",
                resource_type="gamma",
                model=Gamma,
                schema_=GammaSchema,
            ),
            ResourceInfoDTO(
                path="/delta",
                resource_type="delta",
                model=Delta,
                schema_=DeltaSchema,
            ),
        ],
    )


class ResourceInfoDTO(BaseModel):
    path: str
    resource_type: str
    model: type[TypeModel]
    schema_: type[BaseModel]
    schema_in_patch: BaseModel | None = None
    schema_in_post: BaseModel | None = None
    class_list: type[ListViewBase] = ListViewBaseGeneric
    class_detail: type[DetailViewBase] = DetailViewBaseGeneric

    model_config = ConfigDict(arbitrary_types_allowed=True)


def build_custom_app_by_schemas(resources_info: list[ResourceInfoDTO]):
    router: APIRouter = APIRouter()

    for info in resources_info:
        RoutersJSONAPI(
            router=router,
            path=info.path,
            tags=["Misc"],
            class_list=info.class_list,
            class_detail=info.class_detail,
            schema=info.schema_,
            resource_type=info.resource_type,
            schema_in_patch=info.schema_in_patch,
            schema_in_post=info.schema_in_post,
            model=info.model,
        )

    app = build_app_plain()
    app.include_router(router, prefix="")

    atomic = AtomicOperations()
    app.include_router(atomic.router, prefix="")
    init(app)
    return app
