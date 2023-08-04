import logging
from typing import TypeVar

from fastapi_jsonapi.schema import (
    BaseJSONAPIItemInSchema,
    JSONAPIResultDetailSchema,
)
from fastapi_jsonapi.views.utils import HTTPDetailMethod
from fastapi_jsonapi.views.view_base import ViewBase
from fastapi_jsonapi.views.view_handlers import handle_endpoint_dependencies

logger = logging.getLogger(__name__)


TypeModel = TypeVar("TypeModel")


class DetailViewBase(ViewBase):
    # TODO: move to view base?
    async def update_resource_result(
        self,
        obj_id: str,
        data_update: BaseJSONAPIItemInSchema,
        **extra_view_deps,
    ) -> JSONAPIResultDetailSchema:
        dl_kwargs = await handle_endpoint_dependencies(self, HTTPDetailMethod.PATCH, extra_view_deps)
        dl = self._get_data_layer_for_detail(**dl_kwargs)
        view_kwargs = {dl.url_id_field: obj_id}
        db_object = await dl.get_object(view_kwargs=view_kwargs, qs=self.query_params)

        await dl.update_object(db_object, data_update, view_kwargs)

        # TODO: move template code
        result_objects, object_schemas, extras = self.process_includes_for_db_items(
            includes=self.query_params.include,
            # as list to reuse helper
            items_from_db=[db_object],
            item_schema=self.jsonapi.schema_detail,
        )
        # is it ok to do through list?
        result_object = result_objects[0]

        detail_jsonapi_schema = self.jsonapi.schema_builder.build_schema_for_detail_result(
            name=f"Result{self.__class__.__name__}",
            object_jsonapi_schema=object_schemas.object_jsonapi_schema,
            includes_schemas=object_schemas.included_schemas_list,
        )
        return detail_jsonapi_schema(
            data=result_object,
            **extras,
        )

    async def delete_resource_result(
        self,
        obj_id: str,
        **extra_view_deps,
    ):
        dl_kwargs = await handle_endpoint_dependencies(self, HTTPDetailMethod.DELETE, extra_view_deps)
        dl = self._get_data_layer_for_detail(**dl_kwargs)
        view_kwargs = {dl.url_id_field: obj_id}
        db_object = await dl.get_object(view_kwargs=view_kwargs, qs=self.query_params)

        result_objects, object_schemas, extras = self.process_includes_for_db_items(
            includes=self.query_params.include,
            # as list to reuse helper
            items_from_db=[db_object],
            item_schema=self.jsonapi.schema_detail,
        )
        # is it ok to do through list?
        result_object = result_objects[0]

        await dl.delete_object(db_object, view_kwargs)

        # we need to build a new schema here
        # because we'd like to exclude/set some fields (relationships, includes, etc)
        detail_jsonapi_schema = self.jsonapi.schema_builder.build_schema_for_detail_result(
            name=f"Result{self.__class__.__name__}",
            object_jsonapi_schema=object_schemas.object_jsonapi_schema,
            includes_schemas=object_schemas.included_schemas_list,
        )
        return detail_jsonapi_schema(
            data=result_object,
            **extras,
        )
