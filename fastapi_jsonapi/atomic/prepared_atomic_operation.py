from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, Optional, Type

from fastapi import Request

from fastapi_jsonapi import RoutersJSONAPI
from fastapi_jsonapi.atomic.schemas import AtomicOperationAction, AtomicOperationRef, OperationDataType
from fastapi_jsonapi.views.utils import HTTPMethod

if TYPE_CHECKING:
    from fastapi_jsonapi.data_layers.base import BaseDataLayer
    from fastapi_jsonapi.views.detail_view import DetailViewBase
    from fastapi_jsonapi.views.list_view import ListViewBase
    from fastapi_jsonapi.views.view_base import ViewBase

LocalIdsType = Dict[str, Dict[str, str]]


@dataclass
class OperationBase:
    jsonapi: RoutersJSONAPI
    view: ViewBase
    ref: Optional[AtomicOperationRef]
    data: OperationDataType
    op_type: str

    @property
    def http_method(self) -> HTTPMethod:
        raise NotImplementedError

    @classmethod
    def prepare(
        cls,
        action: str,
        request: Request,
        jsonapi: RoutersJSONAPI,
        ref: Optional[AtomicOperationRef],
        data: OperationDataType,
    ) -> "OperationBase":
        view_cls: Type[ViewBase] = jsonapi.detail_view_resource

        if hasattr(action, "value"):
            # convert to str if enum
            action = action.value

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
            op_type=action,
        )

    async def get_data_layer(self) -> BaseDataLayer:
        data_layer_view_dependencies: Dict[str, Any] = await self.jsonapi.handle_view_dependencies(
            request=self.view.request,
            view_cls=self.view.__class__,
            method=self.http_method,
        )
        return await self.view.get_data_layer(data_layer_view_dependencies)

    async def handle(self, dl: BaseDataLayer):
        raise NotImplementedError

    @classmethod
    def upd_one_relationship_with_local_id(cls, relationship_info: dict, local_ids: LocalIdsType):
        """
        TODO: refactor

        :param relationship_info:
        :param local_ids:
        :return:
        """
        missing = object()
        lid = relationship_info.get("lid", missing)
        if lid is missing:
            return

        resource_type = relationship_info["type"]
        if resource_type not in local_ids:
            msg = (
                f"Resource {resource_type!r} not found in previous operations,"
                f" no lid {lid!r} defined yet, cannot create {relationship_info}"
            )
            raise ValueError(msg)

        lids_for_resource = local_ids[resource_type]
        if lid not in lids_for_resource:
            msg = (
                f"lid {lid!r} for {resource_type!r} not found in previous operations,"
                f" cannot process {relationship_info}"
            )
            raise ValueError(msg)

        relationship_info.pop("lid")
        relationship_info["id"] = lids_for_resource[lid]

    def update_relationships_with_lid(self, local_ids: LocalIdsType):
        if not (self.data and self.data.relationships):
            return
        for relationship_name, relationship_value in self.data.relationships.items():
            relationship_data = relationship_value["data"]
            if isinstance(relationship_data, list):
                for data in relationship_data:
                    self.upd_one_relationship_with_local_id(data, local_ids=local_ids)
            elif isinstance(relationship_data, dict):
                self.upd_one_relationship_with_local_id(relationship_data, local_ids=local_ids)
            else:
                msg = "unexpected relationship data"
                raise ValueError(msg)


class ListOperationBase(OperationBase):
    view: ListViewBase


class DetailOperationBase(OperationBase):
    view: DetailViewBase


class OperationAdd(ListOperationBase):
    http_method = HTTPMethod.POST

    async def handle(self, dl: BaseDataLayer):
        # use outer schema wrapper because we need this error path:
        # `{'loc': ['data', 'attributes', 'name']`
        # and not `{'loc': ['attributes', 'name']`
        data_in = self.jsonapi.schema_in_post(data=self.data)
        response = await self.view.process_create_object(
            dl=dl,
            data_create=data_in.data,
        )
        return response


class OperationUpdate(DetailOperationBase):
    http_method = HTTPMethod.PATCH

    async def handle(self, dl: BaseDataLayer):
        if self.data is None:
            # TODO: clear to-one relationships
            pass
        # TODO: handle relationship update requests (relationship resources)

        # use outer schema wrapper because we need this error path:
        # `{'loc': ['data', 'attributes', 'name']`
        # and not `{'loc': ['attributes', 'name']`
        data_in = self.jsonapi.schema_in_patch(data=self.data)
        obj_id = self.ref and self.ref.id or self.data and self.data.id
        response = await self.view.process_update_object(
            dl=dl,
            obj_id=obj_id,
            data_update=data_in.data,
        )
        return response


class OperationRemove(DetailOperationBase):
    http_method = HTTPMethod.DELETE

    async def handle(
        self,
        dl: BaseDataLayer,
    ) -> None:
        """
        Calls view to delete object

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
