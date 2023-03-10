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
from fastapi_jsonapi.data_layers.orm import DBORMType
from .models.pydantic import UserPatchSchema
from .models.pydantic.user import (
    UserSchema, UserInSchema,
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
    RoutersJSONAPI(
        routers=routers,
        path="/user",
        tags=["User"],
        class_detail=UserDetail,
        class_list=UserList,
        schema=UserSchema,
        type_resource="user",
        schema_in_patch=UserPatchSchema,
        schema_in_post=UserInSchema,
        model=User,
        engine=DBORMType.tortoise,
    )

    app.include_router(routers, prefix="")
    return tags
