import logging

from fastapi_jsonapi.schema import (
    BaseJSONAPIDataInSchema,
    JSONAPIResultDetailSchema,
)
from fastapi_jsonapi.views.view_base import ViewBase

logger = logging.getLogger(__name__)


class DetailViewBase(ViewBase):
    async def update_resource_result(
        self,
        obj_id: str,
        data_update: BaseJSONAPIDataInSchema,
    ) -> JSONAPIResultDetailSchema:
        ...
