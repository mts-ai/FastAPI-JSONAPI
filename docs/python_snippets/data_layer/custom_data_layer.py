from fastapi import FastAPI

from fastapi_jsonapi import RoutersJSONAPI
from fastapi_jsonapi.data_layers.base import BaseDataLayer
from fastapi_jsonapi.data_layers.sqla_orm import SqlalchemyDataLayer
from fastapi_jsonapi.views.detail_view import DetailViewBase
from fastapi_jsonapi.views.list_view import ListViewBase


class MyCustomDataLayer(BaseDataLayer):
    """Overload abstract methods here"""

    ...


class MyCustomSqlaDataLayer(SqlalchemyDataLayer):
    """Overload any methods here"""

    async def before_delete_objects(self, objects: list, view_kwargs: dict):
        raise Exception("not allowed to delete objects")


class UserDetailView(DetailViewBase):
    data_layer_cls = MyCustomDataLayer


class UserListView(ListViewBase):
    data_layer_cls = MyCustomDataLayer


app = FastAPI()
RoutersJSONAPI(
    app,
    # ...
    class_detail=UserDetailView,
    class_list=UserListView,
    # ...
)
