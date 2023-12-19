from typing import ClassVar, Dict

from fastapi import Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from examples.api_for_sqlalchemy.extensions.sqlalchemy import Connector
from fastapi_jsonapi.data_layers.sqla_orm import SqlalchemyDataLayer
from fastapi_jsonapi.misc.sqla.generics.base import DetailViewBaseGeneric, ListViewBaseGeneric
from fastapi_jsonapi.views.utils import HTTPMethod, HTTPMethodConfig
from fastapi_jsonapi.views.view_base import ViewBase


class SessionDependency(BaseModel):
    session: AsyncSession = Depends(Connector.get_session)

    class Config:
        arbitrary_types_allowed = True


def handler(view: ViewBase, dto: SessionDependency) -> Dict:
    return {"session": dto.session}


class DetailViewBase(DetailViewBaseGeneric):
    """
    Generic view base (detail)
    """

    data_layer_cls = SqlalchemyDataLayer

    method_dependencies: ClassVar = {
        HTTPMethod.ALL: HTTPMethodConfig(
            dependencies=SessionDependency,
            prepare_data_layer_kwargs=handler,
        ),
    }


class ListViewBase(ListViewBaseGeneric):
    """
    Generic view base (list)
    """

    data_layer_cls = SqlalchemyDataLayer

    method_dependencies: ClassVar = {
        HTTPMethod.ALL: HTTPMethodConfig(
            dependencies=SessionDependency,
            prepare_data_layer_kwargs=handler,
        ),
    }
