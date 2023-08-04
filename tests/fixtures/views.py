from typing import Dict

from fastapi import Depends
from pydantic import BaseModel
from pytest import fixture  # noqa
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_jsonapi.misc.sqla.generics.base import (
    DetailViewBaseGeneric as DetailViewBaseGenericHelper,
)
from fastapi_jsonapi.misc.sqla.generics.base import (
    ListViewBaseGeneric as ListViewBaseGenericHelper,
)
from fastapi_jsonapi.views.utils import HTTPMethod, HTTPMethodConfig
from fastapi_jsonapi.views.view_base import ViewBase
from tests.fixtures.db_connection import async_session_dependency


class SessionDependency(BaseModel):
    session: AsyncSession = Depends(async_session_dependency)

    class Config:
        arbitrary_types_allowed = True


def common_handler(view: ViewBase, dto: BaseModel) -> Dict:
    return {"session": dto.session}


class DetailViewBaseGeneric(DetailViewBaseGenericHelper):
    method_dependencies = {
        HTTPMethod.ALL: HTTPMethodConfig(
            dependencies=SessionDependency,
            handler=common_handler,
        ),
    }


class ListViewBaseGeneric(ListViewBaseGenericHelper):
    method_dependencies = {
        HTTPMethod.ALL: HTTPMethodConfig(
            dependencies=SessionDependency,
            handler=common_handler,
        ),
    }
