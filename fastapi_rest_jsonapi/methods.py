"""Decorators and utils for JSON API routers."""

from inspect import signature
from typing import (
    Any,
    Callable,
    List,
    Optional,
    Type,
    TypeVar,
)

from fastapi import Query
from pydantic import BaseModel
from starlette import status
from starlette.requests import Request
from starlette.responses import Response

from fastapi_rest_jsonapi.pagination import json_api_pagination
from fastapi_rest_jsonapi.querystring import QueryStringManager
from fastapi_rest_jsonapi.signature import (
    is_necessary_request,
    update_signature,
)


def get_detail_jsonapi(schema: Type[BaseModel], type_: str, schema_resp: Any) -> Callable:
    """GET DETAIL method router (Decorator for JSON API)."""

    def inner(func: Callable) -> Callable:
        async def wrapper(request: Request, obj_id: int):
            query_params = QueryStringManager(request=request, schema=schema)
            data_dict: dict = dict(query_params=query_params, obj_id=obj_id)
            if is_necessary_request(func):
                data_dict["request"] = request
            data_schema: Any = await func(**data_dict)
            return schema_resp(
                data={
                    "id": data_schema.id,
                    "attributes": data_schema.dict(),
                },
            )

        return wrapper

    return inner


MODEL = TypeVar("MODEL")


def patch_detail_jsonapi(
    schema: Type[BaseModel],
    schema_in: Type[MODEL],
    type_: str,
    schema_resp: Any,
) -> Callable:
    """
    PATCH method router (Decorator for JSON API).
    TODO: validate `id` in data!
    """

    def inner(func: Callable) -> Callable:
        async def wrapper(request: Request, obj_id: int, data: schema_in):  # type: ignore
            query_params = QueryStringManager(request=request, schema=schema)
            data_dict: dict = dict(query_params=query_params, obj_id=obj_id, data=getattr(data, "attributes", data))
            if is_necessary_request(func):
                data_dict["request"] = request
            data_schema: Any = await func(**data_dict)
            return schema_resp(
                data={
                    "id": data_schema.id,
                    "attributes": data_schema.dict(),
                },
            )

        return wrapper

    return inner


def delete_detail_jsonapi(schema: Type[BaseModel]) -> Callable:
    """DELETE method router (Decorator for JSON API)."""

    def inner(func: Callable) -> Callable:
        async def wrapper(request: Request, obj_id: int):  # type: ignore
            query_params = QueryStringManager(request=request, schema=schema)
            data_dict: dict = dict(query_params=query_params, obj_id=obj_id)
            if is_necessary_request(func):
                data_dict["request"] = request
            await func(**data_dict)
            return Response(status_code=status.HTTP_204_NO_CONTENT)

        return wrapper

    return inner


async def _get_single_response(
    query, query_params: QueryStringManager, schema: Type[BaseModel], type_: str, schema_resp: Any
) -> Any:
    query, total_pages, count = await json_api_pagination(query=query, query_params=query_params)
    data_model: List[Any] = await query.all()
    data_schema: List[Any] = [schema.from_orm(i_obj) for i_obj in data_model]
    return schema_resp(
        data=[{"id": i_obj.id, "attributes": i_obj.dict()} for i_obj in data_schema],
        meta={"count": count, "totalPages": total_pages},
    )


def get_list_jsonapi(schema: Type[BaseModel], type_: str, schema_resp: Any) -> Callable:
    """GET LIST method router (Decorator for JSON API)."""

    def inner(func: Callable) -> Callable:
        async def wrapper(
            request: Request,
            size: int = Query(25, alias="page[size]"),
            number: int = Query(1, alias="page[number]"),
            offset: int = Query(None, alias="page[offset]"),
            limit: Optional[int] = Query(None, alias="page[limit]"),
            filters_list: Optional[str] = Query(
                None,
                alias="filter",
                description="[Filtering docs](https://flask-combo-jsonapi.readthedocs.io/en/latest/filtering.html)"
                "\nExamples:\n* filter for timestamp interval: "
                '`[{"name": "timestamp", "op": "ge", "val": "2020-07-16T11:35:33.383"},'
                '{"name": "timestamp", "op": "le", "val": "2020-07-21T11:35:33.383"}]`',
            ),
            **kwargs,
        ):
            query_params = QueryStringManager(request=request, schema=schema)
            data: dict = dict(query_params=query_params)
            if is_necessary_request(func):
                data["request"] = request

            query = await func(**data)

            if isinstance(query, BaseModel):  # JSONAPIResultListSchema
                return query
            elif isinstance(query, list):
                return schema_resp(data=[{"id": i_obj.id, "attributes": i_obj.dict()} for i_obj in query])
            else:
                return await _get_single_response(query, query_params, schema, type_, schema_resp)  # QuerySet

        # mypy ругается что нет метода __signature__, как это обойти красиво- не знаю
        wrapper.__signature__ = update_signature(sig=signature(wrapper), schema=schema)  # type: ignore
        return wrapper

    return inner


def post_list_jsonapi(
    schema: Type[BaseModel],
    schema_in: Type[BaseModel],
    type_: str,
    schema_resp: Any,
) -> Callable:
    """
    POST method router (Decorator for JSON API).
    TODO: check data in `type` field
    """

    def inner(func: Callable) -> Callable:
        async def wrapper(request: Request, data: schema_in):  # type: ignore
            query_params = QueryStringManager(request=request, schema=schema)
            data_dict: dict = dict(query_params=query_params, data=getattr(data, 'attributes', data))
            if is_necessary_request(func):
                data_dict["request"] = request
            data_pydantic: Any = await func(**data_dict)
            return schema_resp(
                data={
                    "id": data_pydantic.id,
                    "attributes": data_pydantic.dict(),
                },
            )

        return wrapper

    return inner
