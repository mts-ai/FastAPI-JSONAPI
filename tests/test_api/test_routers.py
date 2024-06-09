from typing import ClassVar, Dict, Optional

from fastapi import APIRouter, Depends, FastAPI, Header, Path, status
from httpx import AsyncClient
from pydantic import BaseModel, ConfigDict
from pytest import mark  # noqa
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing_extensions import Annotated

from fastapi_jsonapi import RoutersJSONAPI, init
from fastapi_jsonapi.exceptions import Forbidden, InternalServerError
from fastapi_jsonapi.misc.sqla.generics.base import DetailViewBaseGeneric, ListViewBaseGeneric
from fastapi_jsonapi.views.utils import (
    HTTPMethod,
    HTTPMethodConfig,
)
from fastapi_jsonapi.views.view_base import ViewBase
from tests.fixtures.db_connection import async_session_dependency
from tests.fixtures.views import SessionDependency
from tests.misc.utils import fake
from tests.models import User
from tests.schemas import (
    UserAttributesBaseSchema,
    UserPatchSchema,
    UserInSchema,
    UserSchema,
)

pytestmark = mark.asyncio


def build_app(detail_view, resource_type: str) -> FastAPI:
    app = FastAPI(
        title="FastAPI and SQLAlchemy",
        debug=True,
        openapi_url="/openapi.json",
        docs_url="/docs",
    )
    router: APIRouter = APIRouter()

    RoutersJSONAPI(
        router=router,
        path="/users",
        tags=["User"],
        class_detail=detail_view,
        class_list=ListViewBaseGeneric,
        schema=UserSchema,
        resource_type=resource_type,
        schema_in_patch=UserPatchSchema,
        schema_in_post=UserInSchema,
        model=User,
    )

    app.include_router(router, prefix="")
    init(app)

    return app


async def test_dependency_handler_call():
    def one() -> int:
        return 1

    def two() -> int:
        return 2

    class CustomDependencies(BaseModel):
        dependency_1: int = Depends(one)
        dependency_2: int = Depends(two)

    async def dependencies_handler(view_base: ViewBase, dto: CustomDependencies) -> Optional[Dict]:
        raise InternalServerError(
            detail="hi",
            errors=[
                InternalServerError(
                    title="Check that dependency successfully passed",
                    detail=dto.model_dump(),
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                ),
                InternalServerError(
                    title="Check caller class",
                    detail=view_base.__class__.__name__,
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                ),
            ],
        )

    class DependencyInjectionDetailView(DetailViewBaseGeneric):
        method_dependencies: ClassVar[Dict[HTTPMethod, HTTPMethodConfig]] = {
            HTTPMethod.GET: HTTPMethodConfig(
                dependencies=CustomDependencies,
                prepare_data_layer_kwargs=dependencies_handler,
            ),
        }

    app = build_app(DependencyInjectionDetailView, resource_type="test_dependency_handler_call")
    async with AsyncClient(app=app, base_url="http://test") as client:
        res = await client.get("/users/1")

        assert res.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR, res.text
        assert res.json() == {
            "errors": [
                {
                    "detail": "hi",
                    "meta": [
                        {
                            "detail": {"dependency_1": 1, "dependency_2": 2},
                            "source": {"pointer": ""},
                            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                            "title": "Check that dependency successfully passed",
                        },
                        {
                            "detail": DependencyInjectionDetailView.__name__,
                            "source": {"pointer": ""},
                            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                            "title": "Check caller class",
                        },
                    ],
                    "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                },
            ],
        }


async def test_dependencies_as_permissions(user_1: User):
    async def check_that_user_is_admin(x_auth: Annotated[str, Header()]):
        if x_auth != "admin":
            raise Forbidden(detail="Only admin user have permissions to this endpoint")

    class AdminOnlyPermission(BaseModel):
        is_admin: Optional[bool] = Depends(check_that_user_is_admin)

    def get_path_obj_id(obj_id: int = Path(default=...)):
        return obj_id

    class DetailGenericDependency(SessionDependency):
        custom_name_obj_id: int = Depends(get_path_obj_id)

    def all_handler(view: ViewBase, dto: DetailGenericDependency) -> Dict:
        # test inside handler
        assert dto.custom_name_obj_id == int(view.request.path_params["obj_id"])
        return {"session": dto.session}

    class DependencyInjectionDetailView(DetailViewBaseGeneric):
        method_dependencies: ClassVar[Dict[HTTPMethod, HTTPMethodConfig]] = {
            HTTPMethod.GET: HTTPMethodConfig(dependencies=AdminOnlyPermission),
            HTTPMethod.ALL: HTTPMethodConfig(
                dependencies=DetailGenericDependency,
                prepare_data_layer_kwargs=all_handler,
            ),
        }

    resource_type = fake.word()
    app = build_app(DependencyInjectionDetailView, resource_type=resource_type)
    async with AsyncClient(app=app, base_url="http://test") as client:
        res = await client.get(f"/users/{user_1.id}", headers={"X-AUTH": "not_admin"})

        assert res.status_code == status.HTTP_403_FORBIDDEN, res.text
        assert res.json() == {
            "errors": [
                {
                    "detail": "Only admin user have permissions to this endpoint",
                    "source": {"pointer": ""},
                    "status_code": status.HTTP_403_FORBIDDEN,
                    "title": "Forbidden",
                },
            ],
        }

        res = await client.get(f"/users/{user_1.id}", headers={"X-AUTH": "admin"})
        assert res.json() == {
            "data": {
                "attributes": UserAttributesBaseSchema.model_validate(user_1).model_dump(),
                "id": str(user_1.id),
                "type": resource_type,
            },
            "jsonapi": {"version": "1.0"},
            "meta": None,
        }


async def test_manipulate_data_layer_kwargs(
    user_1: User,
):
    class GetDetailDependencies(BaseModel):
        session: AsyncSession = Depends(async_session_dependency)
        model_config = ConfigDict(arbitrary_types_allowed=True)

    async def set_session_and_ignore_user_1(view_base: ViewBase, dto: GetDetailDependencies) -> Dict:
        query = select(User).where(User.id != user_1.id)

        return {
            "session": dto.session,
            "query": query,
        }

    class DependencyInjectionDetailView(DetailViewBaseGeneric):
        method_dependencies: ClassVar[Dict[HTTPMethod, HTTPMethodConfig]] = {
            HTTPMethod.GET: HTTPMethodConfig(
                dependencies=GetDetailDependencies,
                prepare_data_layer_kwargs=set_session_and_ignore_user_1,
            ),
        }

    app = build_app(DependencyInjectionDetailView, resource_type="test_manipulate_data_layer_kwargs")
    async with AsyncClient(app=app, base_url="http://test") as client:
        res = await client.get(f"/users/{user_1.id}")

        assert res.status_code == status.HTTP_404_NOT_FOUND, res.text
        assert res.json() == {
            "errors": [
                {
                    "detail": f"Resource User `{user_1.id}` not found",
                    "meta": {"parameter": "id"},
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "title": "Resource not found.",
                },
            ],
        }
