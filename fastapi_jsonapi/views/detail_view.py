import logging
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    TypeVar,
    Union,
)

from fastapi_jsonapi import BadRequest
from fastapi_jsonapi.schema import (
    BaseJSONAPIItemInSchema,
    JSONAPIResultDetailSchema,
)
from fastapi_jsonapi.views.view_base import ViewBase

if TYPE_CHECKING:
    from fastapi_jsonapi.data_layers.base import BaseDataLayer

logger = logging.getLogger(__name__)


TypeModel = TypeVar("TypeModel")


class DetailViewBase(ViewBase):
    async def get_data_layer(
        self,
        extra_view_deps: Dict[str, Any],
    ) -> "BaseDataLayer":
        return await self.get_data_layer_for_detail(extra_view_deps)

    async def handle_get_resource_detail(
        self,
        object_id: Union[int, str],
        **extra_view_deps,
    ):
        dl: "BaseDataLayer" = await self.get_data_layer(extra_view_deps)

        view_kwargs = {dl.url_id_field: object_id}
        db_object = await dl.get_object(view_kwargs=view_kwargs, qs=self.query_params)

        return self._build_detail_response(db_object)

    async def handle_update_resource(
        self,
        obj_id: str,
        data_update: BaseJSONAPIItemInSchema,
        **extra_view_deps,
    ) -> JSONAPIResultDetailSchema:
        dl: "BaseDataLayer" = await self.get_data_layer(extra_view_deps)
        return await self.process_update_object(dl=dl, obj_id=obj_id, data_update=data_update)

    async def process_update_object(
        self,
        dl: "BaseDataLayer",
        obj_id: str,
        data_update: BaseJSONAPIItemInSchema,
    ):
        if obj_id != data_update.id:
            raise BadRequest(
                detail="obj_id and data.id should be same",
                pointer="/data/id",
            )
        view_kwargs = {dl.url_id_field: obj_id}
        db_object = await dl.get_object(view_kwargs=view_kwargs, qs=self.query_params)

        await dl.update_object(db_object, data_update, view_kwargs)

        return self._build_detail_response(db_object)

    async def handle_delete_resource(
        self,
        obj_id: str,
        **extra_view_deps,
    ) -> None:
        dl: "BaseDataLayer" = await self.get_data_layer(extra_view_deps)
        await self.process_delete_object(dl=dl, obj_id=obj_id)

    async def process_delete_object(
        self,
        dl: "BaseDataLayer",
        obj_id: str,
    ) -> None:
        view_kwargs = {dl.url_id_field: obj_id}
        db_object = await dl.get_object(view_kwargs=view_kwargs, qs=self.query_params)

        await dl.delete_object(db_object, view_kwargs)
