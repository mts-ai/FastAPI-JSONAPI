import logging
from typing import TypeVar, Union

from fastapi_jsonapi import BadRequest
from fastapi_jsonapi.schema import (
    BaseJSONAPIItemInSchema,
    JSONAPIResultDetailSchema,
)
from fastapi_jsonapi.views.view_base import ViewBase
from fastapi_jsonapi.views.view_handlers import handle_endpoint_dependencies

logger = logging.getLogger(__name__)


TypeModel = TypeVar("TypeModel")


class DetailViewBase(ViewBase):
    async def handle_get_resource_detail(
        self,
        object_id: Union[int, str],
        **extra_view_deps,
    ):
        dl_kwargs = await handle_endpoint_dependencies(self, extra_view_deps)
        dl = self._get_data_layer_for_detail(**dl_kwargs)

        view_kwargs = {dl.url_id_field: object_id}
        db_object = await dl.get_object(view_kwargs=view_kwargs, qs=self.query_params)

        return self._build_detail_response(db_object)

    async def handle_update_resource(
        self,
        obj_id: str,
        data_update: BaseJSONAPIItemInSchema,
        **extra_view_deps,
    ) -> JSONAPIResultDetailSchema:
        if obj_id != data_update.id:
            raise BadRequest(
                detail="obj_id and data.id should be same",
                pointer="/data/id",
            )
        dl_kwargs = await handle_endpoint_dependencies(self, extra_view_deps)
        dl = self._get_data_layer_for_detail(**dl_kwargs)

        view_kwargs = {dl.url_id_field: obj_id}
        db_object = await dl.get_object(view_kwargs=view_kwargs, qs=self.query_params)

        await dl.update_object(db_object, data_update, view_kwargs)

        return self._build_detail_response(db_object)

    async def handle_delete_resource(
        self,
        obj_id: str,
        **extra_view_deps,
    ):
        dl_kwargs = await handle_endpoint_dependencies(self, extra_view_deps)
        dl = self._get_data_layer_for_detail(**dl_kwargs)

        view_kwargs = {dl.url_id_field: obj_id}
        db_object = await dl.get_object(view_kwargs=view_kwargs, qs=self.query_params)

        await dl.delete_object(db_object, view_kwargs)

        return self._build_detail_response(db_object)
