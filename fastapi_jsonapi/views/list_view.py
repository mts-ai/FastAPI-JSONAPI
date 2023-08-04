import logging

from fastapi_jsonapi.schema import (
    BaseJSONAPIDataInSchema,
    JSONAPIResultListMetaSchema,
)
from fastapi_jsonapi.views.utils import HTTPListMethod
from fastapi_jsonapi.views.view_base import ViewBase
from fastapi_jsonapi.views.view_handlers import handle_endpoint_dependencies

logger = logging.getLogger(__name__)


class ListViewBase(ViewBase):
    async def get_resource_list_result(self, **extra_view_deps):
        dl_kwargs = await handle_endpoint_dependencies(
            self,
            HTTPListMethod.GET,
            extra_view_deps,
        )
        dl = self._get_data_layer_for_list(**dl_kwargs)
        query_params = self.query_params
        count, items_from_db = await dl.get_collection(qs=query_params)
        total_pages = 1
        if query_params.pagination.size:
            total_pages = count // query_params.pagination.size + (
                # one more page if not a multiple of size
                (count % query_params.pagination.size)
                and 1
            )

        result_objects, object_schemas, extras = self.process_includes_for_db_items(
            includes=query_params.include,
            items_from_db=items_from_db,
            item_schema=self.jsonapi.schema_list,
        )

        # we need to build a new schema here
        # because we'd like to exclude some fields (relationships, includes, etc)
        list_jsonapi_schema = self.jsonapi.schema_builder.build_schema_for_list_result(
            name=f"Result{self.__class__.__name__}",
            object_jsonapi_schema=object_schemas.object_jsonapi_schema,
            includes_schemas=object_schemas.included_schemas_list,
        )
        return list_jsonapi_schema(
            meta=JSONAPIResultListMetaSchema(count=count, total_pages=total_pages),
            data=result_objects,
            **extras,
        )

    async def post_resource_list_result(
        self,
        data_create: BaseJSONAPIDataInSchema,
        **extra_view_deps,
    ):
        dl_kwargs = await handle_endpoint_dependencies(self, HTTPListMethod.POST, extra_view_deps)
        dl = self._get_data_layer_for_list(**dl_kwargs)
        created_object = await dl.create_object(
            data_create=data_create.data,
            view_kwargs={},
        )
        created_object_id = getattr(created_object, dl.get_object_id_field_name())
        return await self.get_resource_detail_result(object_id=created_object_id, **extra_view_deps)

    async def delete_resource_list_result(self, **extra_view_deps):
        # TODO: move template code
        dl_kwargs = await handle_endpoint_dependencies(
            self,
            HTTPListMethod.DELETE,
            extra_view_deps,
        )
        dl = self._get_data_layer_for_list(**dl_kwargs)
        query_params = self.query_params
        count, items_from_db = await dl.get_collection(qs=query_params)

        total_pages = 1
        if query_params.pagination.size:
            total_pages = count // query_params.pagination.size + (
                # one more page if not a multiple of size
                (count % query_params.pagination.size)
                and 1
            )

        await dl.delete_objects(items_from_db, {})

        result_objects, object_schemas, extras = self.process_includes_for_db_items(
            includes=query_params.include,
            items_from_db=items_from_db,
            item_schema=self.jsonapi.schema_list,
        )

        # we need to build a new schema here
        # because we'd like to exclude some fields (relationships, includes, etc)
        list_jsonapi_schema = self.jsonapi.schema_builder.build_schema_for_list_result(
            name=f"Result{self.__class__.__name__}",
            object_jsonapi_schema=object_schemas.object_jsonapi_schema,
            includes_schemas=object_schemas.included_schemas_list,
        )
        return list_jsonapi_schema(
            meta=JSONAPIResultListMetaSchema(count=count, total_pages=total_pages),
            data=result_objects,
            **extras,
        )
