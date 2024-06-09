from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from fastapi_jsonapi.views.utils import handle_jsonapi_fields
from fastapi_jsonapi.views.view_base import ViewBase

if TYPE_CHECKING:
    from fastapi_jsonapi.data_layers.base import BaseDataLayer
    from fastapi_jsonapi.schema import (
        BaseJSONAPIItemInSchema,
        JSONAPIResultDetailSchema,
        JSONAPIResultListSchema,
    )

logger = logging.getLogger(__name__)


class ListViewBase(ViewBase):
    def _calculate_total_pages(self, db_items_count: int) -> int:
        total_pages = 1
        if not (pagination_size := self.query_params.pagination.size):
            return total_pages

        page, remainder = divmod(db_items_count, pagination_size)
        # add one more page if is not multiple of size
        extra_page = remainder and 1
        return page + extra_page

    async def get_data_layer(
        self,
        extra_view_deps: dict[str, Any],
    ) -> BaseDataLayer:
        return await self.get_data_layer_for_list(extra_view_deps)

    async def handle_get_resource_list(self, **extra_view_deps) -> JSONAPIResultListSchema | dict:
        dl: BaseDataLayer = await self.get_data_layer(extra_view_deps)
        query_params = self.query_params
        count, items_from_db = await dl.get_collection(qs=query_params)
        total_pages = self._calculate_total_pages(count)

        response = self._build_list_response(items_from_db, count, total_pages)
        return handle_jsonapi_fields(response, query_params, self.jsonapi)

    async def handle_post_resource_list(
        self,
        data_create: BaseJSONAPIItemInSchema,
        **extra_view_deps,
    ) -> JSONAPIResultDetailSchema:
        dl: BaseDataLayer = await self.get_data_layer(extra_view_deps)
        response = await self.process_create_object(dl=dl, data_create=data_create)
        return handle_jsonapi_fields(response, self.query_params, self.jsonapi)

    async def process_create_object(
        self,
        dl: BaseDataLayer,
        data_create: BaseJSONAPIItemInSchema,
    ) -> JSONAPIResultDetailSchema:
        created_object = await dl.create_object(data_create=data_create, view_kwargs={})

        created_object_id = dl.get_object_id(created_object)

        view_kwargs = {dl.url_id_field: created_object_id}
        db_object = await dl.get_object(view_kwargs=view_kwargs, qs=self.query_params)

        return self._build_detail_response(db_object)

    async def handle_delete_resource_list(self, **extra_view_deps) -> JSONAPIResultListSchema:
        dl: BaseDataLayer = await self.get_data_layer(extra_view_deps)
        query_params = self.query_params
        count, items_from_db = await dl.get_collection(qs=query_params)
        total_pages = self._calculate_total_pages(count)

        await dl.delete_objects(items_from_db, {})

        response = self._build_list_response(items_from_db, count, total_pages)
        return handle_jsonapi_fields(response, self.query_params, self.jsonapi)
