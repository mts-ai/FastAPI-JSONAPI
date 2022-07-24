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
from .models.pydantic.user import (
    UserJSONAPIDetailSchema,
    UserJSONAPIListSchema,
    UserPatchJSONAPISchema,
    UserPostJSONAPISchema,
    UserSchema,
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
        schema_in_patch=UserPatchJSONAPISchema,
        schema_in_post=UserPostJSONAPISchema,
        resp_schema_detail=UserJSONAPIDetailSchema,
        resp_schema_list=UserJSONAPIListSchema,
    )

    app.include_router(routers, prefix="")
    return tags
