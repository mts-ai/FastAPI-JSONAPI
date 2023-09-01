from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Literal,
    Optional,
    Type,
    Union,
)

from fastapi import APIRouter, Request

from fastapi_jsonapi import RoutersJSONAPI
from fastapi_jsonapi.atomic.schemas import (
    AtomicOperationRequest,
    AtomicResultResponse,
    OperationItemInSchema,
    OperationRelationshipSchema,
)
from fastapi_jsonapi.utils.dependency_helper import DependencyHelper
from fastapi_jsonapi.views.detail_view import DetailViewBase
from fastapi_jsonapi.views.list_view import ListViewBase
from fastapi_jsonapi.views.utils import HTTPMethodConfig
from fastapi_jsonapi.views.view_base import ViewBase

if TYPE_CHECKING:
    from fastapi_jsonapi.data_layers.base import BaseDataLayer


@dataclass
class PreparedOperation:
    action: Literal["add", "update", "remove"]
    data_layer: "BaseDataLayer"
    view: "ViewBase"
    jsonapi: RoutersJSONAPI
    data: Union[
        # from biggest to smallest!
        # any object creation
        OperationItemInSchema,
        # to-many relationship
        List[OperationRelationshipSchema],
        # to-one relationship
        OperationRelationshipSchema,
        # not required
        None,
    ] = None


class AtomicOperations:
    def __init__(
        self,
        url_path: str = "/operations",
        router: Optional[APIRouter] = None,
    ):
        self.router = router or APIRouter(tags=["Atomic Operations"])
        self.url_path = url_path
        self._register_view()

    async def handle_view_dependencies(
        self,
        request: Request,
        jsonapi: RoutersJSONAPI,
    ) -> Dict[str, Any]:
        method_config: HTTPMethodConfig = jsonapi.get_method_config_for_create()

        def handle_dependencies(**dep_kwargs):
            return dep_kwargs

        handle_dependencies.__signature__ = jsonapi.prepare_dependencies_handler_signature(
            custom_handler=handle_dependencies,
            method_config=method_config,
        )

        dependencies_result: Dict[str, Any] = await DependencyHelper(request=request).run(handle_dependencies)
        return dependencies_result

    async def view_atomic(
        self,
        request: Request,
        operations_request: AtomicOperationRequest,
    ):
        prepared_operations: List[PreparedOperation] = []

        for operation in operations_request.operations:
            jsonapi = RoutersJSONAPI.all_jsonapi_routers[operation.data.type]
            view_cls: Type["ViewBase"] = jsonapi.detail_view_resource
            if operation.op == "add":
                view_cls = jsonapi.list_view_resource
            view = view_cls(request=request, jsonapi=jsonapi)
            dependencies_result: Dict[str, Any] = await self.handle_view_dependencies(
                request=request,
                jsonapi=jsonapi,
            )
            dl: "BaseDataLayer" = await view.get_data_layer(dependencies_result)

            one_operation = PreparedOperation(
                action=operation.op,
                data_layer=dl,
                view=view,
                jsonapi=jsonapi,
                data=operation.data,
            )
            prepared_operations.append(one_operation)

        results = []

        # TODO: try/except, catch schema ValidationError

        previous_dl: Optional["BaseDataLayer"] = None
        for operation in prepared_operations:
            dl = operation.data_layer
            await dl.atomic_start(previous_dl=previous_dl)
            previous_dl = dl
            if operation.action == "add":
                data = operation.jsonapi.schema_in_post(data=operation.data)
                assert isinstance(operation.view, ListViewBase)
                view: "ListViewBase" = operation.view
                response = await view.process_create_object(dl=operation.data_layer, data_create=data)
                # response.data.id
                results.append({"data": response.data})
            elif operation.action == "update":
                data = operation.jsonapi.schema_in_patch(data=operation.data)
                assert isinstance(operation.view, DetailViewBase)
                view: "DetailViewBase" = operation.view
                response = await view.process_update_object(
                    dl=dl,
                    obj_id=data.data.id,
                    data_update=data.data,
                )
                # response.data.id
                results.append({"data": response.data})
            elif operation.action == "remove":
                assert isinstance(operation.view, DetailViewBase)
                view: "DetailViewBase" = operation.view
                response = await view.process_delete_object(
                    dl=dl,
                    obj_id=operation.data.id,
                )
                results.append({"data": response.data})
            else:
                msg = f"unknown action {operation.action!r}"
                raise ValueError(msg)

        if previous_dl:
            await previous_dl.atomic_end(success=True)

        return {"atomic:results": results}

    def _register_view(self):
        self.router.add_api_route(
            path=self.url_path,
            endpoint=self.view_atomic,
            response_model=AtomicResultResponse,
            methods=["Post"],
            summary="Atomic operations",
            description="""[https://jsonapi.org/ext/atomic/](https://jsonapi.org/ext/atomic/)""",
        )
