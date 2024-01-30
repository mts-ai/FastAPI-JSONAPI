from typing import ClassVar, Dict

from fastapi import Depends
from pydantic import ConfigDict, BaseModel
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


class ArbitraryModelBase(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)


class SessionDependency(ArbitraryModelBase):
    session: AsyncSession = Depends(async_session_dependency)


def common_handler(view: ViewBase, dto: SessionDependency) -> Dict:
    return {"session": dto.session}


class DetailViewBaseGeneric(DetailViewBaseGenericHelper):
    method_dependencies: ClassVar = {
        HTTPMethod.ALL: HTTPMethodConfig(
            dependencies=SessionDependency,
            prepare_data_layer_kwargs=common_handler,
        ),
    }


class ListViewBaseGeneric(ListViewBaseGenericHelper):
    method_dependencies: ClassVar = {
        HTTPMethod.ALL: HTTPMethodConfig(
            dependencies=SessionDependency,
            prepare_data_layer_kwargs=common_handler,
        ),
    }
