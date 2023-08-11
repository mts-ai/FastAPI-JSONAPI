from fastapi import FastAPI

from fastapi_jsonapi import RoutersJSONAPI
from fastapi_jsonapi.data_layers.base import BaseDataLayer
from fastapi_jsonapi.views.detail_view import DetailViewBase
from fastapi_jsonapi.views.list_view import ListViewBase


class MyCustomDataLayer(BaseDataLayer):
    """Overload abstract methods here"""


class PersonDetailView(DetailViewBase):
    data_layer_cls = MyCustomDataLayer


class PersonListView(ListViewBase):
    data_layer_cls = MyCustomDataLayer


app = FastAPI()
RoutersJSONAPI(
    app,
    # ...
    class_detail=PersonDetailView,
    class_list=PersonListView,
    # ...
)
