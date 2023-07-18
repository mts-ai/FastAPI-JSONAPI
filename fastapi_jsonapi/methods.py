"""Decorators and utils for JSON API routers."""
import inspect
from collections import OrderedDict
from inspect import signature
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Type,
    Union,
)

from fastapi import Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from starlette.requests import Request
from starlette.responses import Response

from fastapi_jsonapi.data_layers.data_typing import TypeModel
from fastapi_jsonapi.data_layers.orm import DBORMType
from fastapi_jsonapi.data_layers.sqla_orm import SqlalchemyDataLayer
from fastapi_jsonapi.data_layers.tortoise_orm import TortoiseDataLayer
from fastapi_jsonapi.exceptions.json_api import UnsupportedFeatureORM
from fastapi_jsonapi.querystring import QueryStringManager
from fastapi_jsonapi.schema import JSONAPIResultDetailSchema, JSONAPIResultListSchema
from fastapi_jsonapi.signature import update_signature


class ViewHelper:
    def __init__(
        self,
        request: Request,
        schema: Type[BaseModel],
        obj_id: Union[int, str, None] = None,
        schema_in: Optional[Type[BaseModel]] = None,
        input_data: Optional[BaseModel] = None,
    ):
        """
        :param request:
        :param schema:
        :param obj_id:
        :param schema_in:
            TODO:
             1. any name.
             2. any type:
                - JSON:API accepts only str, but view funcs may accept int, uuid, etc
        :param input_data:
        """
        self.schema: Type[BaseModel] = schema
        self.request: Request = request
        self.obj_id: Union[int, str, None] = obj_id
        self.schema_in: Optional[Type[BaseModel]] = schema_in
        self.input_data: Optional[BaseModel] = input_data

    def prepare_depends_kwargs(
        self,
        func_params: Mapping[str, inspect.Parameter],
    ) -> Dict[str, Any]:
        """
        :param func_params:
        :return:
        """
        data_dict = {}
        # TODO: why ordered dict? old solution 🤔
        for i_name, i_type in OrderedDict(func_params).items():
            if i_type.annotation is Request:
                data_dict[i_name] = self.request
            elif i_type.annotation is QueryStringManager:
                data_dict[i_name] = QueryStringManager(request=self.request, schema=self.schema)
            elif (self.schema_in is not None) and (i_type.annotation is self.schema_in.__fields__["attributes"].type_):
                # TODO: Pydantic V2 .__fields__ -> .fields
                # TODO: XXX refactor (old solution)
                #  or get rid of it at all...
                data_dict[i_name] = getattr(self.input_data, "attributes", self.input_data)

        return data_dict

    async def call_original_view(
        self,
        view_func: Callable,
        view_func_kwargs: Dict[str, Any],
    ):
        func_signature = signature(view_func)
        func_params = func_signature.parameters

        kw = self.prepare_depends_kwargs(
            func_params=func_params,
        )
        if self.obj_id is not None:
            # TODO: any name? any type?
            kw["obj_id"] = self.obj_id

        kw.update(view_func_kwargs)
        safe_kwargs = {i_k: i_v for i_k, i_v in kw.items() if i_k in func_params}

        is_awaitable = inspect.isawaitable(view_func) or inspect.iscoroutinefunction(view_func)
        result = view_func(**safe_kwargs)
        if is_awaitable:
            result = await result
        return result


def get_detail_jsonapi(
    schema: Type[BaseModel],
    schema_resp: Any,
    model: Type[TypeModel],
    engine: DBORMType,
) -> Callable:
    """GET DETAIL method router (Decorator for JSON API)."""

    def inner(func: Callable) -> Callable:
        async def wrapper(request: Request, obj_id: int, **kwargs):
            vh = ViewHelper(
                request=request,
                schema=schema,
                obj_id=obj_id,
            )
            data_schema = await vh.call_original_view(
                view_func=func,
                view_func_kwargs=kwargs,
            )
            if isinstance(data_schema, JSONAPIResultDetailSchema):
                return data_schema
            if isinstance(data_schema, dict):
                # todo: do we need it?
                return data_schema

            return schema_resp(
                data={
                    "id": data_schema.id,
                    "attributes": data_schema.dict(),
                },
            )

        # mypy ругается что нет метода __signature__, как это обойти красиво- не знаю
        wrapper.__signature__ = update_signature(  # type: ignore
            sig=signature(wrapper),
            schema=schema,
            other=OrderedDict(signature(func).parameters),
            exclude_filters=True,
        )

        return wrapper

    return inner


def patch_detail_jsonapi(
    schema: Type[BaseModel],
    schema_in: Type[BaseModel],
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
            vh = ViewHelper(
                request=request,
                schema=schema,
                obj_id=obj_id,
                schema_in=schema_in,
                input_data=data,
            )
            data_schema = await vh.call_original_view(
                view_func=func,
                view_func_kwargs=kwargs,
            )
            if isinstance(data_schema, JSONAPIResultDetailSchema):
                return data_schema
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
            vh = ViewHelper(
                request=request,
                schema=schema,
                obj_id=obj_id,
            )
            await vh.call_original_view(
                view_func=func,
                view_func_kwargs=kwargs,
            )
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
            vh = ViewHelper(
                request=request,
                schema=schema,
            )
            await vh.call_original_view(
                view_func=func,
                view_func_kwargs=kwargs,
            )
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
    session: Optional[AsyncSession] = None,
) -> Any:
    """
    TODO: move logic to data layers, get rid of this func
    Also will fix this issue:
    https://github.com/mts-ai/FastAPI-JSONAPI/issues/21
    """
    if engine is DBORMType.sqlalchemy:
        dl = SqlalchemyDataLayer(schema=schema, model=model, session=session, query=query)
    elif engine is DBORMType.tortoise:
        dl = TortoiseDataLayer(schema=schema, model=model, query=query)
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
                None,
                alias="sort",
                description="[Sorting docs](https://fastapi-jsonapi.readthedocs.io/en/latest/sorting.html)",
            ),
            **kwargs,
        ):
            vh = ViewHelper(
                request=request,
                schema=schema,
            )
            query = await vh.call_original_view(
                view_func=func,
                view_func_kwargs=kwargs,
            )

            if isinstance(query, JSONAPIResultListSchema):
                return query

            if isinstance(query, list):
                return schema_resp(
                    data=[{"id": i_obj.id, "attributes": i_obj.dict(), "type": type_} for i_obj in query],
                )

            session = None
            query_params = QueryStringManager(request=request, schema=schema)
            func_signature = signature(func).parameters

            if engine is DBORMType.sqlalchemy:
                # Для SQLAlchemy нужно указывать session, для Tortoise достаточно модели
                session: Optional[AsyncSession] = next(
                    # get first of type AsyncSession or None if not found
                    filter(lambda v: isinstance(v, AsyncSession), func_signature.values()),
                    None,
                )
            if engine is DBORMType.sqlalchemy and session is None:
                msg = "For SQLAlchemy you need to specify session in parameter"
                raise UnsupportedFeatureORM(msg)
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
            # return_annotation=schema_resp,
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
            vh = ViewHelper(
                request=request,
                schema=schema,
                schema_in=schema_in,
                input_data=data,
            )
            data_pydantic = await vh.call_original_view(
                view_func=func,
                view_func_kwargs=kwargs,
            )
            if isinstance(data_pydantic, JSONAPIResultDetailSchema):
                return data_pydantic
            return schema_resp(
                data={
                    "id": data_pydantic.id,
                    "attributes": data_pydantic.dict(),
                },
            )

        # mypy ругается что нет метода __signature__, как это обойти красиво- не знаю
        wrapper.__signature__ = update_signature(  # type: ignore
            sig=signature(wrapper),
            schema=schema,
            other=OrderedDict(signature(func).parameters),
            exclude_filters=True,
        )

        return wrapper

    return inner
