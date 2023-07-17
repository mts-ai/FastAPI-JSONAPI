import logging
from typing import Any, Type

from fastapi_jsonapi import (
    QueryStringManager,
)
from fastapi_jsonapi.data_layers.base import BaseDataLayer
from fastapi_jsonapi.data_layers.data_typing import TypeSchema
from fastapi_jsonapi.schema import (
    JSONAPIResultListMetaSchema,
    JSONAPIResultListSchema,
)
from fastapi_jsonapi.views.view_base import ViewBase

logger = logging.getLogger(__name__)


class ListViewBase(ViewBase):
    def _get_data_layer(self, **kwargs: Any) -> BaseDataLayer:
        """
        :param kwargs: Any extra kwargs for the data layer. if
        :return:
        """
        return self.data_layer_cls(
            schema=self.jsonapi.schema_list,
            model=self.jsonapi.model,
            **kwargs,
        )

    async def get_view_result(self, query_params: QueryStringManager, **kwargs):
        dl = self._get_data_layer(**kwargs)
        return await self.get_paginated_result(
            dl=dl,
            query_params=query_params,
        )

    async def get_paginated_result(
        self,
        dl: BaseDataLayer,
        query_params: QueryStringManager,
        schema: Type[TypeSchema] = None,
    ) -> JSONAPIResultListSchema:
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
            item_schema=schema or self.jsonapi.schema_list,
        )

        # we need to build a new schema here
        # because we'd like to exclude some fields (relationships, includes, etc)
        list_jsonapi_schema = self.jsonapi.build_schema_for_list_result(
            name=f"Result{self.__class__.__name__}",
            object_jsonapi_schema=object_schemas.object_jsonapi_schema,
            includes_schemas=object_schemas.included_schemas_list,
        )
        return list_jsonapi_schema(
            meta=JSONAPIResultListMetaSchema(count=count, total_pages=total_pages),
            data=result_objects,
            **extras,
        )
