import logging
from typing import TYPE_CHECKING, Any, Dict

from fastapi_jsonapi.schema import (
    BaseJSONAPIItemInSchema,
    JSONAPIResultDetailSchema,
    JSONAPIResultListSchema,
)
from fastapi_jsonapi.views.view_base import ViewBase

if TYPE_CHECKING:
    from fastapi_jsonapi.data_layers.base import BaseDataLayer

logger = logging.getLogger(__name__)


class ListViewBase(ViewBase):
    def _calculate_total_pages(self, db_items_count: int) -> int:
        total_pages = 1
        if not (pagination_size := self.query_params.pagination.size):
            return total_pages

        total_pages = db_items_count // pagination_size + (
            # one more page if not a multiple of size
            (db_items_count % pagination_size)
            and 1
        )

        return total_pages

    async def get_data_layer(
        self,
        extra_view_deps: Dict[str, Any],
    ) -> "BaseDataLayer":
        return await self.get_data_layer_for_list(extra_view_deps)

    async def handle_get_resource_list(self, **extra_view_deps) -> JSONAPIResultListSchema:
        dl: "BaseDataLayer" = await self.get_data_layer(extra_view_deps)
        query_params = self.query_params
        count, items_from_db = await dl.get_collection(qs=query_params)
        total_pages = self._calculate_total_pages(count)

        return self._build_list_response(items_from_db, count, total_pages)

    async def handle_post_resource_list(
        self,
        data_create: BaseJSONAPIItemInSchema,
        **extra_view_deps,
    ) -> JSONAPIResultDetailSchema:
        dl: "BaseDataLayer" = await self.get_data_layer(extra_view_deps)
        return await self.process_create_object(dl=dl, data_create=data_create)

    async def process_create_object(self, dl: "BaseDataLayer", data_create: BaseJSONAPIItemInSchema):
        created_object = await dl.create_object(data_create=data_create, view_kwargs={})

        created_object_id = dl.get_object_id(created_object)

        view_kwargs = {dl.url_id_field: created_object_id}
        db_object = await dl.get_object(view_kwargs=view_kwargs, qs=self.query_params)

        return self._build_detail_response(db_object)

    async def handle_delete_resource_list(self, **extra_view_deps) -> JSONAPIResultListSchema:
        dl: "BaseDataLayer" = await self.get_data_layer(extra_view_deps)
        query_params = self.query_params
        count, items_from_db = await dl.get_collection(qs=query_params)
        total_pages = self._calculate_total_pages(count)

        await dl.delete_objects(items_from_db, {})

        return self._build_list_response(items_from_db, count, total_pages)
