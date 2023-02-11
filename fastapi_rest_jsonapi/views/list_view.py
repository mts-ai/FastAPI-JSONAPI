import logging

from fastapi_rest_jsonapi import (
    QueryStringManager,
    SqlalchemyEngine,
)
from fastapi_rest_jsonapi.schema import (
    JSONAPIResultListMetaSchema,
    JSONAPIResultListSchema,
)
from fastapi_rest_jsonapi.views.view_base import ViewBase


logger = logging.getLogger(__name__)


class ListViewBase(ViewBase):
    async def get_paginated_result(
        self,
        dl: SqlalchemyEngine,
        query_params: QueryStringManager,
    ) -> JSONAPIResultListSchema:
        # todo: generate dl?
        count, items_from_db = await dl.get_collection(qs=query_params)
        total_pages = 1
        if query_params.pagination.size:
            total_pages = count // query_params.pagination.size + (
                (count % query_params.pagination.size) and 1  # noqa: S001
            )

        result_objects, extras = self.process_includes_for_db_items(
            includes=query_params.include,
            items_from_db=items_from_db,
        )
        return self.jsonapi.list_response_schema(
            meta=JSONAPIResultListMetaSchema(count=count, total_pages=total_pages),
            data=result_objects,
            **extras,
        )
