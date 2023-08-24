from fastapi_jsonapi.data_layers.sqla_orm import SqlalchemyDataLayer
from fastapi_jsonapi.views.detail_view import DetailViewBase
from fastapi_jsonapi.views.list_view import ListViewBase


class DetailViewBaseGeneric(DetailViewBase):
    data_layer_cls = SqlalchemyDataLayer


class ListViewBaseGeneric(ListViewBase):
    data_layer_cls = SqlalchemyDataLayer
