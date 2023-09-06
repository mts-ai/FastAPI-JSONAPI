from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, Optional, Type

from fastapi import Request

from fastapi_jsonapi import RoutersJSONAPI
from fastapi_jsonapi.atomic.schemas import AtomicOperationAction, AtomicOperationRef, OperationDataType

if TYPE_CHECKING:
    from fastapi_jsonapi.data_layers.base import BaseDataLayer
    from fastapi_jsonapi.views.detail_view import DetailViewBase
    from fastapi_jsonapi.views.list_view import ListViewBase
    from fastapi_jsonapi.views.view_base import ViewBase


@dataclass
class OperationBase:
    jsonapi: RoutersJSONAPI
    view: ViewBase
    ref: Optional[AtomicOperationRef]
    data: OperationDataType
    data_layer_view_dependencies: Dict[str, Any]

    @classmethod
    def prepare(
        cls,
        action: str,
        request: Request,
        jsonapi: RoutersJSONAPI,
        ref: Optional[AtomicOperationRef],
        data: OperationDataType,
        data_layer_view_dependencies: Dict[str, Any],
    ) -> "OperationBase":
        view_cls: Type[ViewBase] = jsonapi.detail_view_resource

        if action == AtomicOperationAction.add:
            operation_cls = OperationAdd
            view_cls = jsonapi.list_view_resource
        elif action == AtomicOperationAction.update:
            operation_cls = OperationUpdate
        elif action == AtomicOperationAction.remove:
            operation_cls = OperationRemove
        else:
            msg = f"Unknown operation {action!r}"
            raise ValueError(msg)

        view = view_cls(request=request, jsonapi=jsonapi)

        return operation_cls(
            jsonapi=jsonapi,
            view=view,
            ref=ref,
            data=data,
            data_layer_view_dependencies=data_layer_view_dependencies,
        )

    async def get_data_layer(self) -> BaseDataLayer:
        return await self.view.get_data_layer(self.data_layer_view_dependencies)

    async def handle(self, dl: BaseDataLayer):
        raise NotImplementedError


class ListOperationBase(OperationBase):
    view: ListViewBase


class DetailOperationBase(OperationBase):
    view: DetailViewBase


class OperationAdd(ListOperationBase):
    async def handle(self, dl: BaseDataLayer):
        data_in = self.jsonapi.schema_in_post(data=self.data)
        response = await self.view.process_create_object(
            dl=dl,
            data_create=data_in.data,
        )
        return response


class OperationUpdate(DetailOperationBase):
    async def handle(self, dl: BaseDataLayer):
        data_in = self.jsonapi.schema_in_patch(data=self.data)
        obj_id = self.ref and self.ref.id or self.data and self.data.id
        response = await self.view.process_update_object(
            dl=dl,
            obj_id=obj_id,
            data_update=data_in.data,
        )
        return response


class OperationRemove(DetailOperationBase):
    async def handle(
        self,
        dl: BaseDataLayer,
    ) -> None:
        """
        Todo: fix atomic delete
         Deleting Resources
           An operation that deletes a resource
           MUST target that resource
           through the operation’s ref or href members,
           but not both.

        :param dl:
        :return:
        """
        await self.view.process_delete_object(
            dl=dl,
            obj_id=self.ref and self.ref.id,
        )
