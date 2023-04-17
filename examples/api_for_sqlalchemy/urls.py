"""Route creator"""

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
from .api.post import PostDetail, PostList
from .api.user_bio import UserBioDetail, UserBioList
from .models.schemas import (
    UserSchema,
    UserInSchema,
    UserPatchSchema,
    PostSchema,
    PostInSchema,
    PostPatchSchema,
    UserBioSchema,
    UserBioPatchSchema,
    UserBioInSchema,
)
from .api.user import (
    UserDetail,
    UserList,
)
from examples.api_for_sqlalchemy.models import User, Post, UserBio


def add_routes(app: FastAPI) -> List[Dict[str, Any]]:
    tags = [
        {
            "name": "User",
            "description": "Users API",
        },
        {
            "name": "Post",
            "description": "Posts API",
        },
    ]

    routers: APIRouter = APIRouter()
    RoutersJSONAPI(
        routers=routers,
        path="/users",
        tags=["User"],
        class_detail=UserDetail,
        class_list=UserList,
        schema=UserSchema,
        type_resource="user",
        schema_in_patch=UserPatchSchema,
        schema_in_post=UserInSchema,
        model=User,
        engine=DBORMType.sqlalchemy,
    )

    RoutersJSONAPI(
        routers=routers,
        path="/posts",
        tags=["Post"],
        class_detail=PostDetail,
        class_list=PostList,
        schema=PostSchema,
        type_resource="post",
        schema_in_patch=PostPatchSchema,
        schema_in_post=PostInSchema,
        model=Post,
        engine=DBORMType.sqlalchemy,
    )

    RoutersJSONAPI(
        routers=routers,
        path="/user-bio",
        tags=["Bio"],
        class_detail=UserBioDetail,
        class_list=UserBioList,
        schema=UserBioSchema,
        type_resource="user_bio",
        schema_in_patch=UserBioPatchSchema,
        schema_in_post=UserBioInSchema,
        model=UserBio,
        engine=DBORMType.sqlalchemy,
    )

    app.include_router(routers, prefix="")
    return tags
