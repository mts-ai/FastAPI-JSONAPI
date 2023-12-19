from typing import (
    Optional,
    Type,
)

from fastapi import APIRouter, Request, Response, status

from fastapi_jsonapi.atomic.atomic_handler import AtomicViewHandler
from fastapi_jsonapi.atomic.schemas import (
    AtomicOperationRequest,
    AtomicResultResponse,
)


class AtomicOperations:
    atomic_handler: Type[AtomicViewHandler] = AtomicViewHandler

    def __init__(
        self,
        url_path: str = "/operations",
        router: Optional[APIRouter] = None,
    ):
        self.router = router or APIRouter(tags=["Atomic Operations"])
        self.url_path = url_path
        self._register_view()

    async def view_atomic(
        self,
        request: Request,
        operations_request: AtomicOperationRequest,
    ):
        atomic_handler = self.atomic_handler(
            request=request,
            operations_request=operations_request,
        )
        result = await atomic_handler.handle()
        if result:
            return result
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    def _register_view(self) -> None:
        self.router.add_api_route(
            path=self.url_path,
            endpoint=self.view_atomic,
            response_model=AtomicResultResponse,
            methods=["Post"],
            summary="Atomic operations",
            description="""[https://jsonapi.org/ext/atomic/](https://jsonapi.org/ext/atomic/)""",
        )
