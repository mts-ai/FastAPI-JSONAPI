from pathlib import Path
from typing import Optional, Type

import pytest
from fastapi import APIRouter, FastAPI
from pydantic import BaseModel, ConfigDict

from examples.api_for_sqlalchemy.models import (
    AgeRating,
    Child,
    Computer,
    Movie,
    Parent,
    ParentToChildAssociation,
    Post,
    PostComment,
    User,
    UserBio,
)
from examples.api_for_sqlalchemy.schemas import (
    AgeRatingCreateSchema,
    AgeRatingSchema,
    AgeRatingUpdateSchema,
    ChildInSchema,
    ChildPatchSchema,
    ChildSchema,
    ComputerInSchema,
    ComputerPatchSchema,
    ComputerSchema,
    MovieCreateSchema,
    MovieSchema,
    MovieUpdateSchema,
    ParentPatchSchema,
    ParentSchema,
    ParentToChildAssociationSchema,
    PostCommentSchema,
    PostInSchema,
    PostPatchSchema,
    PostSchema,
    UserBioBaseSchema,
    UserInSchema,
    UserPatchSchema,
    UserSchema,
)
from fastapi_jsonapi import ApplicationBuilder
from fastapi_jsonapi.atomic import AtomicOperations
from fastapi_jsonapi.data_typing import TypeModel
from fastapi_jsonapi.views.view_base import ViewBase

from .models import Alpha, Beta, CustomUUIDItem, Delta, Gamma, Task
from .schemas import (
    AlphaSchema,
    BetaSchema,
    CustomUUIDItemSchema,
    DeltaSchema,
    GammaSchema,
    TaskInSchema,
    TaskPatchSchema,
    TaskSchema,
)
from .views import ViewBaseGeneric

CURRENT_DIR = Path(__file__).resolve().parent
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
    builder = ApplicationBuilder(app=app_plain, base_router=router)
    builder.add_resource(
        path="/children",
        tags=["Child"],
        resource_type="child",
        view=ViewBaseGeneric,
        schema=ChildSchema,
        schema_in_patch=ChildPatchSchema,
        schema_in_post=ChildInSchema,
        model=Child,
    )
    builder.add_resource(
        path="/comments",
        tags=["Comment"],
        resource_type="post_comment",
        view=ViewBaseGeneric,
        schema=PostCommentSchema,
        model=PostComment,
    )
    builder.add_resource(
        path="/computers",
        tags=["Computer"],
        resource_type="computer",
        view=ViewBaseGeneric,
        model=Computer,
        schema=ComputerSchema,
        schema_in_patch=ComputerPatchSchema,
        schema_in_post=ComputerInSchema,
    )
    builder.add_resource(
        path="/custom-uuid-item",
        tags=["Custom UUID Item"],
        resource_type="custom_uuid_item",
        view=ViewBaseGeneric,
        model=CustomUUIDItem,
        schema=CustomUUIDItemSchema,
    )
    builder.add_resource(
        path="/parent-to-child-association",
        tags=["Parent To Child Association"],
        resource_type="parent-to-child-association",
        view=ViewBaseGeneric,
        model=ParentToChildAssociation,
        schema=ParentToChildAssociationSchema,
    )
    builder.add_resource(
        path="/parents",
        tags=["Parent"],
        resource_type="parent",
        view=ViewBaseGeneric,
        model=Parent,
        schema=ParentSchema,
        schema_in_patch=ParentPatchSchema,
        schema_in_post=ParentPatchSchema,
    )
    builder.add_resource(
        path="/posts",
        tags=["Post"],
        resource_type="post",
        view=ViewBaseGeneric,
        schema=PostSchema,
        schema_in_patch=PostPatchSchema,
        schema_in_post=PostInSchema,
        model=Post,
    )
    builder.add_resource(
        path="/tasks",
        tags=["Task"],
        resource_type="task",
        view=ViewBaseGeneric,
        model=Task,
        schema=TaskSchema,
        schema_in_patch=TaskPatchSchema,
        schema_in_post=TaskInSchema,
    )
    builder.add_resource(
        path="/user-bio",
        tags=["Bio"],
        resource_type="user_bio",
        model=UserBio,
        view=ViewBaseGeneric,
        schema=UserBioBaseSchema,
    )
    builder.add_resource(
        path="/users",
        tags=["User"],
        resource_type="user",
        view=ViewBaseGeneric,
        model=User,
        schema=UserSchema,
        schema_in_patch=UserPatchSchema,
        schema_in_post=UserInSchema,
    )
    builder.add_resource(
        path="/age-ratings",
        tags=["Age Ratings"],
        resource_type="age-rating",
        view=ViewBaseGeneric,
        model=AgeRating,
        schema=AgeRatingSchema,
        schema_in_post=AgeRatingCreateSchema,
        schema_in_patch=AgeRatingUpdateSchema,
        model_id_field_name="name",
    )
    builder.add_resource(
        path="/movies",
        tags=["Movie"],
        resource_type="movie",
        view=ViewBaseGeneric,
        model=Movie,
        schema=MovieSchema,
        schema_in_post=MovieCreateSchema,
        schema_in_patch=MovieUpdateSchema,
    )
    builder.initialize()

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
    view: Type[ViewBase] = ViewBaseGeneric,
) -> FastAPI:
    router: APIRouter = APIRouter()
    app = build_app_plain()
    builder = ApplicationBuilder(app=app)
    builder.add_resource(
        router=router,
        path=path,
        tags=["Misc"],
        view=view,
        schema=schema,
        resource_type=resource_type,
        schema_in_patch=schema_in_patch,
        schema_in_post=schema_in_post,
        model=model,
    )
    builder.initialize()

    app.include_router(router, prefix="")

    atomic = AtomicOperations()
    app.include_router(atomic.router, prefix="")

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
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    path: str
    resource_type: str
    model: Type[TypeModel]
    schema_: Type[BaseModel]
    schema_in_patch: Optional[BaseModel] = None
    schema_in_post: Optional[BaseModel] = None
    view: Type[ViewBase] = ViewBaseGeneric


def build_custom_app_by_schemas(resources_info: list[ResourceInfoDTO]):
    router: APIRouter = APIRouter()
    app = build_app_plain()
    builder = ApplicationBuilder(app)

    for info in resources_info:
        builder.add_resource(
            router=router,
            path=info.path,
            tags=["Misc"],
            view=ViewBaseGeneric,
            schema=info.schema_,
            resource_type=info.resource_type,
            schema_in_patch=info.schema_in_patch,
            schema_in_post=info.schema_in_post,
            model=info.model,
        )

    builder.initialize()
    app.include_router(router, prefix="")

    atomic = AtomicOperations()
    app.include_router(atomic.router, prefix="")

    return app
