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

from .api.child import ChildDetail, ChildList
from .api.parent import ParentDetail, ParentList
from .api.post import PostDetail, PostList
from .api.user_bio import UserBioDetail, UserBioList
from .api.views_base import DetailViewBase, ListViewBase
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
        class_detail=DetailViewBase,
        class_list=ListViewBase,
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
        class_detail=PostDetail,
        class_list=PostList,
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
        class_detail=UserBioDetail,
        class_list=UserBioList,
        schema=UserBioSchema,
        resource_type="user_bio",
        schema_in_patch=UserBioPatchSchema,
        schema_in_post=UserBioInSchema,
        model=UserBio,
    )

    RoutersJSONAPI(
        router=router,
        path="/parents",
        tags=["Parent"],
        class_detail=ParentDetail,
        class_list=ParentList,
        schema=ParentSchema,
        resource_type="parent",
        schema_in_patch=PostPatchSchema,
        schema_in_post=PostInSchema,
        model=Parent,
    )

    RoutersJSONAPI(
        router=router,
        path="/children",
        tags=["Child"],
        class_detail=ChildDetail,
        class_list=ChildList,
        schema=ChildSchema,
        resource_type="child",
        schema_in_patch=ChildPatchSchema,
        schema_in_post=ChildInSchema,
        model=Child,
    )

    app.include_router(router, prefix="")
    return tags
