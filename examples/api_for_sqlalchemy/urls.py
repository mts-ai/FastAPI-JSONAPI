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

from examples.api_for_sqlalchemy.models import (
    Child,
    Computer,
    Parent,
    ParentToChildAssociation,
    Post,
    User,
    UserBio,
)
from fastapi_jsonapi import RoutersJSONAPI
from fastapi_jsonapi.atomic import AtomicOperations

from .api.views_base import DetailViewBase, ListViewBase
from .models.schemas import (
    ChildInSchema,
    ChildPatchSchema,
    ChildSchema,
    ComputerInSchema,
    ComputerPatchSchema,
    ComputerSchema,
    ParentInSchema,
    ParentPatchSchema,
    ParentSchema,
    ParentToChildAssociationSchema,
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
        model=User,
        schema=UserSchema,
        resource_type="user",
        schema_in_patch=UserPatchSchema,
        schema_in_post=UserInSchema,
    )

    RoutersJSONAPI(
        router=router,
        path="/posts",
        tags=["Post"],
        class_detail=DetailViewBase,
        class_list=ListViewBase,
        model=Post,
        schema=PostSchema,
        resource_type="post",
        schema_in_patch=PostPatchSchema,
        schema_in_post=PostInSchema,
    )

    RoutersJSONAPI(
        router=router,
        path="/user-bio",
        tags=["Bio"],
        class_detail=DetailViewBase,
        class_list=ListViewBase,
        model=UserBio,
        schema=UserBioSchema,
        resource_type="user_bio",
        schema_in_patch=UserBioPatchSchema,
        schema_in_post=UserBioInSchema,
    )

    RoutersJSONAPI(
        router=router,
        path="/parents",
        tags=["Parent"],
        class_detail=DetailViewBase,
        class_list=ListViewBase,
        model=Parent,
        schema=ParentSchema,
        resource_type="parent",
        schema_in_patch=ParentPatchSchema,
        schema_in_post=ParentInSchema,
    )

    RoutersJSONAPI(
        router=router,
        path="/children",
        tags=["Child"],
        class_detail=DetailViewBase,
        class_list=ListViewBase,
        model=Child,
        schema=ChildSchema,
        resource_type="child",
        schema_in_patch=ChildPatchSchema,
        schema_in_post=ChildInSchema,
    )

    RoutersJSONAPI(
        router=router,
        path="/parent-to-child-association",
        tags=["Parent To Child Association"],
        class_detail=DetailViewBase,
        class_list=ListViewBase,
        schema=ParentToChildAssociationSchema,
        resource_type="parent-to-child-association",
        model=ParentToChildAssociation,
    )

    RoutersJSONAPI(
        router=router,
        path="/computers",
        tags=["Computer"],
        class_detail=DetailViewBase,
        class_list=ListViewBase,
        model=Computer,
        schema=ComputerSchema,
        resource_type="computer",
        schema_in_patch=ComputerPatchSchema,
        schema_in_post=ComputerInSchema,
    )

    atomic = AtomicOperations()

    app.include_router(router, prefix="")
    app.include_router(atomic.router, prefix="")
    return tags
