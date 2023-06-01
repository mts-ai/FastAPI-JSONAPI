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

from examples.api_for_sqlalchemy.models import Child, Parent, Post, User, UserBio
from fastapi_jsonapi import RoutersJSONAPI
from fastapi_jsonapi.data_layers.orm import DBORMType

from .api.child import ChildDetail, ChildList
from .api.parent import ParentDetail, ParentList
from .api.post import PostDetail, PostList
from .api.user import (
    UserDetail,
    UserList,
)
from .api.user_bio import UserBioDetail, UserBioList
from .models.schemas import (
    ChildInSchema,
    ChildPatchSchema,
    ChildSchema,
    ParentSchema,
    PostInSchema,
    PostPatchSchema,
    PostSchema,
    UserBioInSchema,
    UserBioPatchSchema,
    UserBioSchema,
    UserInSchema,
    UserPatchSchema,
    UserSchema,
)


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

    router: APIRouter = APIRouter()
    RoutersJSONAPI(
        router=router,
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
        router=router,
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
        router=router,
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

    RoutersJSONAPI(
        router=router,
        path="/parents",
        tags=["Parent"],
        class_detail=ParentDetail,
        class_list=ParentList,
        schema=ParentSchema,
        type_resource="parent",
        schema_in_patch=PostPatchSchema,
        schema_in_post=PostInSchema,
        model=Parent,
        engine=DBORMType.sqlalchemy,
    )

    RoutersJSONAPI(
        router=router,
        path="/children",
        tags=["Child"],
        class_detail=ChildDetail,
        class_list=ChildList,
        schema=ChildSchema,
        type_resource="child",
        schema_in_patch=ChildPatchSchema,
        schema_in_post=ChildInSchema,
        model=Child,
        engine=DBORMType.sqlalchemy,
    )

    app.include_router(router, prefix="")
    return tags
