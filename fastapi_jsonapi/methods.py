"""Decorators and utils for JSON API routers."""
from collections import OrderedDict
from inspect import signature
from typing import (
    Any,
    Callable,
    List,
    Optional,
    Type,
    TypeVar,
)

from fastapi import Query, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from starlette.requests import Request
from starlette.responses import Response

from fastapi_jsonapi.data_layers.data_typing import TypeModel
from fastapi_jsonapi.data_layers.orm import DBORMType
from fastapi_jsonapi.data_layers.sqlalchemy_engine import SqlalchemyEngine
from fastapi_jsonapi.data_layers.tortoise_orm_engine import TortoiseORMEngine
from fastapi_jsonapi.exceptions.json_api import UnsupportedFeatureORM
from fastapi_jsonapi.querystring import QueryStringManager
from fastapi_jsonapi.signature import update_signature


def get_detail_jsonapi(
    schema: Type[BaseModel],
    type_: str,
    schema_resp: Any,
    model: Type[TypeModel],
    engine: DBORMType,
) -> Callable:
    """GET DETAIL method router (Decorator for JSON API)."""

    def inner(func: Callable) -> Callable:
        async def wrapper(request: Request, obj_id: int, **kwargs):
            query_params = QueryStringManager(request=request, schema=schema)
            data_dict = {"obj_id": obj_id}
            func_signature = signature(func).parameters
            for i_name, i_type in OrderedDict(func_signature).items():
                if i_type.annotation is Request:
                    data_dict[i_name] = request
                elif i_type.annotation is QueryStringManager:
                    data_dict[i_name] = query_params

            data_dict.update({i_k: i_v for i_k, i_v in kwargs.items() if i_k in func_signature})
            data_dict = {i_k: i_v for i_k, i_v in data_dict.items() if i_k in func_signature}
            data_schema: Any = await func(**data_dict)
            return schema_resp(
                data={
                    "id": data_schema.id,
                    "attributes": data_schema.dict(),
                },
            )

        # mypy ругается что нет метода __signature__, как это обойти красиво- не знаю
        wrapper.__signature__ = update_signature(  # type: ignore
            sig=signature(wrapper),
            other=OrderedDict(signature(func).parameters),
        )

        return wrapper

    return inner


MODEL = TypeVar("MODEL")


def patch_detail_jsonapi(
    schema: Type[BaseModel],
    schema_in: Type[MODEL],
    type_: str,
    schema_resp: Any,
    model: Type[TypeModel],
    engine: DBORMType,
) -> Callable:
    """
    PATCH method router (Decorator for JSON API).
    TODO: validate `id` in data!
    """

    def inner(func: Callable) -> Callable:
        async def wrapper(request: Request, obj_id: int, data: schema_in, **kwargs):  # type: ignore
            query_params = QueryStringManager(request=request, schema=schema)
            data_dict = {"obj_id": obj_id}
            func_signature = signature(func).parameters
            for i_name, i_type in OrderedDict(func_signature).items():
                if i_type.annotation is schema_in.__fields__["attributes"].type_:
                    data_dict[i_name] = getattr(data, 'attributes', data)
                elif i_type.annotation is Request:
                    data_dict[i_name] = request
                elif i_type.annotation is QueryStringManager:
                    data_dict[i_name] = query_params

            data_dict.update({i_k: i_v for i_k, i_v in kwargs.items() if i_k in func_signature})
            data_dict = {i_k: i_v for i_k, i_v in data_dict.items() if i_k in func_signature}
            data_schema: Any = await func(**data_dict)
            return schema_resp(
                data={
                    "id": data_schema.id,
                    "attributes": data_schema.dict(),
                },
            )

        # mypy ругается что нет метода __signature__, как это обойти красиво- не знаю
        wrapper.__signature__ = update_signature(  # type: ignore
            sig=signature(wrapper),
            other=OrderedDict(signature(func).parameters),
        )

        return wrapper

    return inner


def delete_detail_jsonapi(
    schema: Type[BaseModel],
    model: Type[TypeModel],
    engine: DBORMType,
) -> Callable:
    """DELETE method router (Decorator for JSON API)."""

    def inner(func: Callable) -> Callable:
        async def wrapper(request: Request, obj_id: int, **kwargs):  # type: ignore
            query_params = QueryStringManager(request=request, schema=schema)
            data_dict = {"obj_id": obj_id}
            func_signature = signature(func).parameters
            for i_name, i_type in OrderedDict(func_signature).items():
                if i_type.annotation is Request:
                    data_dict[i_name] = request
                elif i_type.annotation is QueryStringManager:
                    data_dict[i_name] = query_params

            data_dict.update({i_k: i_v for i_k, i_v in kwargs.items() if i_k in func_signature})
            data_dict = {i_k: i_v for i_k, i_v in data_dict.items() if i_k in func_signature}
            await func(**data_dict)
            return Response(status_code=status.HTTP_204_NO_CONTENT)

        # mypy ругается что нет метода __signature__, как это обойти красиво- не знаю
        wrapper.__signature__ = update_signature(  # type: ignore
            sig=signature(wrapper),
            other=OrderedDict(signature(func).parameters),
        )
        return wrapper

    return inner


def delete_list_jsonapi(
    schema: Type[BaseModel],
    model: Type[TypeModel],
    engine: DBORMType,
) -> Callable:
    """DELETE method router (Decorator for JSON API)."""

    def inner(func: Callable) -> Callable:
        async def wrapper(
            request: Request,
            filters_list: Optional[str] = Query(
                None,
                alias="filter",
                description="[Filtering docs](https://fastapi-jsonapi.readthedocs.io/en/latest/filtering.html)"
                            "\nExamples:\n* filter for timestamp interval: "
                            '`[{"name": "timestamp", "op": "ge", "val": "2020-07-16T11:35:33.383"},'
                            '{"name": "timestamp", "op": "le", "val": "2020-07-21T11:35:33.383"}]`',
            ),
            **kwargs,
        ):
            query_params = QueryStringManager(request=request, schema=schema)
            data_dict = {}
            func_signature = signature(func).parameters
            for i_name, i_type in OrderedDict(func_signature).items():
                if i_type.annotation is Request:
                    data_dict[i_name] = request
                elif i_type.annotation is QueryStringManager:
                    data_dict[i_name] = query_params

            params_function = OrderedDict(signature(func).parameters)
            data_dict.update({i_k: i_v for i_k, i_v in kwargs.items() if i_k in params_function})
            data_dict = {i_k: i_v for i_k, i_v in data_dict.items() if i_k in params_function}
            await func(**data_dict)
            return Response(status_code=status.HTTP_204_NO_CONTENT)

        # mypy ругается что нет метода __signature__, как это обойти красиво- не знаю
        wrapper.__signature__ = update_signature(  # type: ignore
            sig=signature(wrapper),
            schema=schema,
            other=OrderedDict(signature(func).parameters),
        )
        return wrapper

    return inner


async def _get_single_response(
    query,
    query_params: QueryStringManager,
    schema: Type[BaseModel],
    type_: str,
    schema_resp: Any,
    model: Type[TypeModel],
    engine: DBORMType,
    session: Optional[AsyncSession] = None
) -> Any:
    if engine is DBORMType.sqlalchemy:
        dl = SqlalchemyEngine(schema=schema, model=model, session=session, query=query)
    elif engine is DBORMType.tortoise:
        dl = TortoiseORMEngine(schema=schema, model=model, query=query)
    else:
        raise UnsupportedFeatureORM()

    count, data_model = await dl.get_collection(qs=query_params, view_kwargs={})
    total_pages = count // query_params.pagination.size + (count % query_params.pagination.size and 1)

    data_schema: List[Any] = [schema.from_orm(i_obj) for i_obj in data_model]
    return schema_resp(
        data=[{"id": i_obj.id, "attributes": i_obj.dict(), "type": type_} for i_obj in data_schema],
        meta={"count": count, "totalPages": total_pages},
    )


def get_list_jsonapi(
    schema: Type[BaseModel],
    type_: str,
    schema_resp: Any,
    model: Type[TypeModel],
    engine: DBORMType,
) -> Callable:
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
                description="[Filtering docs](https://fastapi-jsonapi.readthedocs.io/en/latest/filtering.html)"
                "\nExamples:\n* filter for timestamp interval: "
                '`[{"name": "timestamp", "op": "ge", "val": "2020-07-16T11:35:33.383"},'
                '{"name": "timestamp", "op": "le", "val": "2020-07-21T11:35:33.383"}]`',
            ),
            sort: Optional[str] = Query(
                None, alias='sort', 
                description="[Sorting docs](https://fastapi-jsonapi.readthedocs.io/en/latest/sorting.html)"
            ),
            **kwargs,
        ):
            query_params = QueryStringManager(request=request, schema=schema)
            data_dict = {}
            func_signature = signature(func).parameters
            for i_name, i_type in OrderedDict(func_signature).items():
                if i_type.annotation is Request:
                    data_dict[i_name] = request
                elif i_type.annotation is QueryStringManager:
                    data_dict[i_name] = query_params

            data_dict.update({i_k: i_v for i_k, i_v in kwargs.items() if i_k in func_signature})
            data_dict = {i_k: i_v for i_k, i_v in data_dict.items() if i_k in func_signature}
            query = await func(**data_dict)

            if engine is DBORMType.sqlalchemy:
                # Для SQLAlchemy нужно указывать session, для Tortoise достаточно модели
                session_list = [i_v for i_k, i_v in func_signature.items() if isinstance(i_v, AsyncSession)]
                session: Optional[AsyncSession] = session_list and session_list[0] or None
            else:
                session = None

            if isinstance(query, BaseModel):  # JSONAPIResultListSchema
                return query
            elif isinstance(query, list):
                return schema_resp(data=[{"id": i_obj.id, "attributes": i_obj.dict(), "type": type_} for i_obj in query])
            else:
                if engine is DBORMType.sqlalchemy and session is None:
                    raise UnsupportedFeatureORM("For SQLAlchemy you need to specify session in parameter")
                return await _get_single_response(
                    query,
                    query_params,
                    schema,
                    type_,
                    schema_resp,
                    model=model,
                    engine=engine,
                    session=session,
                )  # QuerySet

        # mypy ругается что нет метода __signature__, как это обойти красиво- не знаю
        wrapper.__signature__ = update_signature(  # type: ignore
            sig=signature(wrapper),
            schema=schema,
            other=OrderedDict(signature(func).parameters),
        )
        return wrapper

    return inner


def post_list_jsonapi(
    schema: Type[BaseModel],
    schema_in: Type[BaseModel],
    type_: str,
    schema_resp: Any,
    model: Type[TypeModel],
    engine: DBORMType,
) -> Callable:
    """
    POST method router (Decorator for JSON API).
    TODO: check data in `type` field
    """

    def inner(func: Callable) -> Callable:
        async def wrapper(request: Request, data: schema_in, **kwargs):  # type: ignore
            query_params = QueryStringManager(request=request, schema=schema)
            data_dict = {}
            func_signature = signature(func).parameters
            for i_name, i_type in OrderedDict(func_signature).items():
                if i_type.annotation is schema_in.__fields__["attributes"].type_:
                    data_dict[i_name] = getattr(data, 'attributes', data)
                elif i_type.annotation is Request:
                    data_dict[i_name] = request
                elif i_type.annotation is QueryStringManager:
                    data_dict[i_name] = query_params

            params_function = OrderedDict(func_signature)
            data_dict.update({i_k: i_v for i_k, i_v in kwargs.items() if i_k in params_function})
            data_dict = {i_k: i_v for i_k, i_v in data_dict.items() if i_k in params_function}
            data_pydantic: Any = await func(**data_dict)
            return schema_resp(
                data={
                    "id": data_pydantic.id,
                    "attributes": data_pydantic.dict(),
                },
            )

        # mypy ругается что нет метода __signature__, как это обойти красиво- не знаю
        wrapper.__signature__ = update_signature(  # type: ignore
            sig=signature(wrapper),
            other=OrderedDict(signature(func).parameters),
        )

        return wrapper

    return inner
