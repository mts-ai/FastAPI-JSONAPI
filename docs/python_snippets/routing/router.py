from fastapi import APIRouter, FastAPI

from examples.api_for_sqlalchemy.models import User
from examples.api_for_sqlalchemy.models.schemas import (
    UserInSchema,
    UserPatchSchema,
    UserSchema,
)
from fastapi_jsonapi import RoutersJSONAPI
from fastapi_jsonapi.misc.sqla.generics.base import DetailViewBase, ListViewBase


def add_routes(app: FastAPI):
    tags = [
        {
            "name": "User",
            "description": "Users API",
        },
    ]

    router: APIRouter = APIRouter()
    RoutersJSONAPI(
        router=router,
        path="/users",
        tags=["User"],
        class_detail=DetailViewBase,
        class_list=ListViewBase,
        model=User,
        schema=UserSchema,
        resource_type="user",
        schema_in_patch=UserPatchSchema,
        schema_in_post=UserInSchema,
    )

    app.include_router(router, prefix="")
    return tags


app = FastAPI()
add_routes(app)
