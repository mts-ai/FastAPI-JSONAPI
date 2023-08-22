import logging

from fastapi_jsonapi.schema import (
    BaseJSONAPIDataInSchema,
    JSONAPIResultDetailSchema,
    JSONAPIResultListSchema,
)
from fastapi_jsonapi.views.view_base import ViewBase
from fastapi_jsonapi.views.view_handlers import handle_endpoint_dependencies

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

    async def handle_get_resource_list(self, **extra_view_deps) -> JSONAPIResultListSchema:
        dl_kwargs = await handle_endpoint_dependencies(self, extra_view_deps)
        dl = self._get_data_layer_for_list(**dl_kwargs)
        query_params = self.query_params
        count, items_from_db = await dl.get_collection(qs=query_params)
        total_pages = self._calculate_total_pages(count)

        return self._build_list_response(items_from_db, count, total_pages)

    async def handle_post_resource_list(
        self,
        data_create: BaseJSONAPIDataInSchema,
        **extra_view_deps,
    ) -> JSONAPIResultDetailSchema:
        dl_kwargs = await handle_endpoint_dependencies(self, extra_view_deps)
        dl = self._get_data_layer_for_list(**dl_kwargs)
        created_object = await dl.create_object(data_create=data_create.data, view_kwargs={})
        created_object_id = getattr(created_object, dl.get_object_id_field_name())

        view_kwargs = {dl.url_id_field: created_object_id}
        db_object = await dl.get_object(view_kwargs=view_kwargs, qs=self.query_params)

        return self._build_detail_response(db_object)

    async def handle_delete_resource_list(self, **extra_view_deps) -> JSONAPIResultListSchema:
        dl_kwargs = await handle_endpoint_dependencies(self, extra_view_deps)
        dl = self._get_data_layer_for_list(**dl_kwargs)
        query_params = self.query_params
        count, items_from_db = await dl.get_collection(qs=query_params)
        total_pages = self._calculate_total_pages(count)

        await dl.delete_objects(items_from_db, {})

        return self._build_list_response(items_from_db, count, total_pages)
