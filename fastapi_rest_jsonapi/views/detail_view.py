import logging
from typing import Dict

from fastapi_rest_jsonapi import SqlalchemyEngine, QueryStringManager
from fastapi_rest_jsonapi.schema import JSONAPIResultDetailSchema
from fastapi_rest_jsonapi.views.view_base import ViewBase


logger = logging.getLogger(__name__)


class DetailViewBase(ViewBase):
    async def get_detailed_result(
        self,
        dl: SqlalchemyEngine,
        view_kwargs: Dict[str, str],
        query_params: QueryStringManager = None,
    ) -> JSONAPIResultDetailSchema:
        # todo: generate dl?
        db_object = await dl.get_object(view_kwargs=view_kwargs, qs=query_params)

        result_objects, extras = self.process_includes_for_db_items(
            includes=query_params.include,
            items_from_db=[db_object],
        )
        result_object = result_objects[0]
        return self.jsonapi.detail_response_schema(
            data=result_object,
            **extras,
        )
