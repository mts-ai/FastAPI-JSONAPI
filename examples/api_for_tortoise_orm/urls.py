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

from fastapi_rest_jsonapi import RoutersJSONAPI
from .models.pydantic import UserPatchSchema
from .models.pydantic.user import (
    UserSchema, UserInSchema,
)
from .api.user import (
    UserDetail,
    UserList,
)


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
        type_resource="users",
        schema_in_patch=UserPatchSchema,
        schema_in_post=UserInSchema,
    )

    app.include_router(routers, prefix="")
    return tags
