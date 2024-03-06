import logging
from typing import TYPE_CHECKING, Any, Dict

from fastapi_jsonapi.schema import (
    BaseJSONAPIItemInSchema,
    JSONAPIResultDetailSchema,
    JSONAPIResultListSchema,
)
from fastapi_jsonapi.views.utils import get_includes_indexes_by_type
from fastapi_jsonapi.views.view_base import ViewBase

if TYPE_CHECKING:
    from fastapi_jsonapi.data_layers.base import BaseDataLayer

logger = logging.getLogger(__name__)


def calculate_include_fields(response, query_params, jsonapi) -> Dict:
    included = "included" in response.__fields__ and response.included or []

    include_params = {
        field_name: {*response.__fields__[field_name].type_.__fields__.keys()}
        for field_name in response.__fields__
        if field_name
    }
    include_params["included"] = {}

    includes_indexes_by_type = get_includes_indexes_by_type(included)

    for resource_type, field_names in query_params.fields.items():
        if resource_type == jsonapi.type_:
            include_params["data"] = {"__all__": {"attributes": field_names, "id": {"id"}, "type": {"type"}}}
            continue

        target_type_indexes = includes_indexes_by_type.get(resource_type)

        if resource_type in includes_indexes_by_type and target_type_indexes:
            include_params["included"].update((idx, field_names) for idx in target_type_indexes)

    return include_params


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

        response = self._build_list_response(items_from_db, count, total_pages)

        if not query_params.fields:
            return response

        include_params = calculate_include_fields(response, query_params, self.jsonapi)

        if include_params:
            return response.dict(include=include_params)

        return response

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
