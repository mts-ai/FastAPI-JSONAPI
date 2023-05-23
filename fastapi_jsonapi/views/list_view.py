import logging
from typing import Type

from fastapi_jsonapi import (
    QueryStringManager,
    SqlalchemyEngine,
)
from fastapi_jsonapi.data_layers.data_typing import TypeSchema
from fastapi_jsonapi.schema import (
    JSONAPIResultListMetaSchema,
    JSONAPIResultListSchema,
)
from fastapi_jsonapi.views.view_base import ViewBase

logger = logging.getLogger(__name__)


class ListViewBase(ViewBase):
    async def get_paginated_result(
        self,
        dl: SqlalchemyEngine,
        query_params: QueryStringManager,
        schema: Type[TypeSchema] = None,
    ) -> JSONAPIResultListSchema:
        # todo: generate dl?
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
