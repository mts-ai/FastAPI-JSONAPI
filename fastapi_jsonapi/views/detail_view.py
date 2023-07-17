import logging
from typing import Any, Dict

from fastapi_jsonapi.data_layers.base import BaseDataLayer
from fastapi_jsonapi.querystring import QueryStringManager
from fastapi_jsonapi.views.view_base import ViewBase

logger = logging.getLogger(__name__)


class DetailViewBase(ViewBase):
    def _get_data_layer(self, **kwargs: Any) -> BaseDataLayer:
        """
        :param kwargs: Any extra kwargs for the data layer. if
        :return:
        """
        return self.data_layer_cls(
            schema=self.jsonapi.schema_detail,
            model=self.jsonapi.model,
            **kwargs,
        )

    async def get_view_result(
        self,
        query_params: QueryStringManager,
        view_kwargs: Dict[str, Any],
        **kwargs: Any,
    ):
        dl = self._get_data_layer(**kwargs)
        return await self.get_detailed_result(
            dl=dl,
            view_kwargs=view_kwargs,
            query_params=query_params,
        )
