from fastapi import Depends
from pydantic import BaseModel

from fastapi_jsonapi.misc.sqla.generics.base import DetailViewBaseGeneric
from fastapi_jsonapi.views.utils import HTTPMethod, HTTPMethodConfig
from fastapi_jsonapi.views.view_base import ViewBase


def one():
    return 1


def two():
    return 2


class CommonDependency(BaseModel):
    key_1: int = Depends(one)


class GetDependency(BaseModel):
    key_2: int = Depends(two)


class DependencyMix(CommonDependency, GetDependency):
    pass


def common_handler(view: ViewBase, dto: CommonDependency) -> dict:
    return {"key_1": dto.key_1}


def get_handler(view: ViewBase, dto: DependencyMix):
    return {"key_2": dto.key_2}


class DetailView(DetailViewBaseGeneric):
    method_dependencies = {
        HTTPMethod.ALL: HTTPMethodConfig(
            dependencies=CommonDependency,
            prepare_data_layer_kwargs=common_handler,
        ),
        HTTPMethod.GET: HTTPMethodConfig(
            dependencies=GetDependency,
            prepare_data_layer_kwargs=get_handler,
        ),
    }
