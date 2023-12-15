"""Route creator for w_mount service."""

from typing import (
    Any,
    Dict,
    List,
)

from fastapi import (
    APIRouter,
    FastAPI,
)

from fastapi_jsonapi import RoutersJSONAPI
from .models.pydantic import UserPatchSchema
from .models.pydantic.user import (
    UserSchema,
    UserInSchema,
)
from .api.user import (
    UserDetail,
    UserList,
)
from .models.tortoise import User


def add_routes(app: FastAPI) -> List[Dict[str, Any]]:
    tags = [
        {
            "name": "User",
            "description": "",
        },
    ]

    routers: APIRouter = APIRouter()
    # TODO: fix example
    RoutersJSONAPI(
        router=routers,
        path="/users",
        tags=["User"],
        class_detail=UserDetail,
        class_list=UserList,
        schema=UserSchema,
        resource_type="user",
        schema_in_patch=UserPatchSchema,
        schema_in_post=UserInSchema,
        model=User,
    )

    app.include_router(routers, prefix="")
    return tags
