from __future__ import annotations

import logging
from collections import defaultdict
from contextvars import ContextVar
from functools import wraps
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    List,
    Optional,
    TypedDict,
    Union,
)

from fastapi import HTTPException, status
from pydantic import ValidationError
from starlette.requests import Request

from fastapi_jsonapi import RoutersJSONAPI
from fastapi_jsonapi.atomic.prepared_atomic_operation import LocalIdsType, OperationBase
from fastapi_jsonapi.atomic.schemas import AtomicOperation, AtomicOperationRequest, AtomicResultResponse

if TYPE_CHECKING:
    from fastapi_jsonapi.data_layers.base import BaseDataLayer

log = logging.getLogger(__name__)
AtomicResponseDict = TypedDict("AtomicResponseDict", {"atomic:results": List[Any]})

current_atomic_operation: ContextVar[OperationBase] = ContextVar("current_atomic_operation")


def catch_exc_on_operation_handle(func: Callable[..., Awaitable]):
    @wraps(func)
    async def wrapper(*a, operation: OperationBase, **kw):
        try:
            return await func(*a, operation=operation, **kw)
        except (ValidationError, ValueError) as ex:
            log.exception(
                "Validation error on atomic action ref=%s, data=%s",
                operation.ref,
                operation.data,
            )
            errors_details = {
                "message": f"Validation error on operation {operation.op_type}",
                "ref": operation.ref,
                "data": operation.data.dict(),
            }
            if isinstance(ex, ValidationError):
                errors_details.update(errors=ex.errors())
            elif isinstance(ex, ValueError):
                errors_details.update(error=str(ex))
            else:
                raise
            # TODO: json:api exception
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=errors_details,
            )

    return wrapper


class AtomicViewHandler:
    def __init__(
        self,
        request: Request,
        operations_request: AtomicOperationRequest,
    ):
        self.request = request
        self.operations_request = operations_request
        self.local_ids_cache: LocalIdsType = defaultdict(dict)

    async def prepare_one_operation(self, operation: AtomicOperation):
        """
        Prepare one atomic operation

        :param operation:
        :return:
        """
        operation_type = operation.ref and operation.ref.type or operation.data and operation.data.type
        assert operation_type
        if operation_type not in RoutersJSONAPI.all_jsonapi_routers:
            msg = f"Unknown resource type {operation_type!r}. Register it via RoutersJSONAPI"
            raise ValueError(msg)
        jsonapi = RoutersJSONAPI.all_jsonapi_routers[operation_type]

        one_operation = OperationBase.prepare(
            action=operation.op,
            request=self.request,
            jsonapi=jsonapi,
            ref=operation.ref,
            data=operation.data,
        )
        return one_operation

    async def prepare_operations(self) -> List[OperationBase]:
        prepared_operations: List[OperationBase] = []

        for operation in self.operations_request.operations:
            one_operation = await self.prepare_one_operation(operation)
            prepared_operations.append(one_operation)

        return prepared_operations

    @catch_exc_on_operation_handle
    async def process_one_operation(
        self,
        dl: BaseDataLayer,
        operation: OperationBase,
    ):
        operation.update_relationships_with_lid(local_ids=self.local_ids_cache)
        return await operation.handle(dl=dl)

    async def handle(self) -> Union[AtomicResponseDict, AtomicResultResponse, None]:
        prepared_operations = await self.prepare_operations()
        results = []
        only_empty_responses = True
        success = True
        previous_dl: Optional[BaseDataLayer] = None
        for operation in prepared_operations:
            # set context var
            ctx_var_token = current_atomic_operation.set(operation)

            dl: BaseDataLayer = await operation.get_data_layer()
            await dl.atomic_start(previous_dl=previous_dl)
            response = await self.process_one_operation(
                dl=dl,
                operation=operation,
            )
            previous_dl = dl

            # response.data.id
            if not response:
                # https://jsonapi.org/ext/atomic/#result-objects
                # An empty result object ({}) is acceptable
                # for operations that are not required to return data.
                results.append({})
                continue
            only_empty_responses = False
            results.append({"data": response.data})
            if operation.data.lid and response.data:
                self.local_ids_cache[operation.data.type][operation.data.lid] = response.data.id

            # reset context var
            current_atomic_operation.reset(ctx_var_token)

        if previous_dl:
            await previous_dl.atomic_end(success=success)

        if not only_empty_responses:
            return {"atomic:results": results}

        """
        if all results are empty,
        the server MAY respond with 204 No Content and no document.
        """
