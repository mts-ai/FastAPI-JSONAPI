"""JSON API router class."""

from typing import (
    Any,
    Dict,
    List,
    Optional,
    Type,
    Union, TypeVar,
)

import pydantic
from fastapi import APIRouter
from pydantic import BaseModel, Field

from fastapi_jsonapi.data_layers.data_typing import TypeModel
from fastapi_jsonapi.data_layers.orm import DBORMType
from fastapi_jsonapi.exceptions import ExceptionResponseSchema
from fastapi_jsonapi.methods import (
    delete_detail_jsonapi,
    get_detail_jsonapi,
    get_list_jsonapi,
    patch_detail_jsonapi,
    post_list_jsonapi, delete_list_jsonapi,
)
from fastapi_jsonapi.schema import BasePatchJSONAPISchema, BasePostJSONAPISchema, JSONAPIObjectSchema, \
    JSONAPIResultDetailSchema

JSON_API_RESPONSE_TYPE = Optional[Dict[Union[int, str], Dict[str, Any]]]

TypeAPIRouter = TypeVar("TypeAPIRouter", bound=APIRouter)
TypeSchema = TypeVar("TypeSchema", bound=BaseModel)


class RoutersJSONAPI:
    """API Router interface for JSON API endpoints in web-services."""

    def __init__(  # noqa: WPS211
        self,
        routers: TypeAPIRouter,
        path: Union[str, List[str]],
        tags: List[str],
        class_detail: Any,
        class_list: Any,
        schema: Type[TypeSchema],
        type_resource: str,
        schema_in_patch: Type[TypeSchema],
        schema_in_post: Type[TypeSchema],
        model: Type[TypeModel],
        engine: DBORMType = DBORMType.sqlalchemy,
    ) -> None:
        """
        Initialize router items.

        :params routers: роутер FastAPI.
        :params path: префикс для API.
        :params tags: теги для swagger, под которыми будет отображаться данный ресурс.
        :params class_detail: класс, в котором есть два @classmethod: get (для выгрузки конкретного элемента)
                              и patch (для частичного обновления конкретного элемента).
        :params class_list: класс, в котором есть два @classmethod: get (для выгрузки списка элементов)
                              и post (для создания нового элемента).
        :params schema: pydantic схема ресурса (полная)
        :params type_resource: тип ресурса, будет отображаться при выгрузке, необходимый параметр JSON:API.
        :params schema_in_patch: pydantic схема с полями, которые можно изменять.
        :params schema_in_post: pydantic схема с полями, которые нужно отправлять для создания новой сущности.
        :params model: Модель данных, например модель данных от SQLAlchemy или Tortoise ORM.
        :params engine: тип движка, какой тип моделей нужно использовать, например SQLAlchemy или Tortoise ORM.
                        Необходимо для автоматического построения запросов.
        """
        self._routers: APIRouter = routers
        self._path: Union[str, List[str]] = path
        self._tags: List[str] = tags
        self.class_detail: Any = class_detail
        self.class_list: Any = class_list
        self._type: str = type_resource
        self._schema: Type[BaseModel] = schema
        self._model: Type[TypeModel] = model
        self._engine: DBORMType = engine

        patch_jsonapi_schema = pydantic.create_model(
            "{base_name}JSONAPI".format(base_name=schema_in_patch.__name__),
            attributes=(schema_in_patch, ...),
            type=(str, Field(default=self._type, description="Тип ресурса")),
            __base__=BasePatchJSONAPISchema,
        )
        self._schema_in_patch_base: Type[BaseModel] = schema_in_patch
        self._schema_in_patch: Type[BaseModel] = patch_jsonapi_schema

        post_jsonapi_schema = pydantic.create_model(
            "{base_name}JSONAPI".format(base_name=schema_in_post.__name__),
            attributes=(schema_in_post, ...),
            type=(str, Field(default=self._type, description="Тип ресурса")),
            __base__=BasePostJSONAPISchema,
        )
        self._schema_in_post_base: Type[BaseModel] = schema_in_post
        self._schema_in_post: Type[BaseModel] = post_jsonapi_schema

        object_jsonapi_schema = pydantic.create_model(
            "{base_name}ObjectJSONAPI".format(base_name=schema.__name__),
            attributes=(schema, ...),
            type=(str, Field(default=self._type, description="Тип ресурса")),
            __base__=JSONAPIObjectSchema,
        )
        detail_jsonapi_schema = pydantic.create_model(
            "{base_name}DetailJSONAPI".format(base_name=schema.__name__),
            data=(object_jsonapi_schema, ...),
            __base__=JSONAPIResultDetailSchema,
        )
        self._resp_schema_detail: Type[BaseModel] = detail_jsonapi_schema
        list_jsonapi_schema = pydantic.create_model(
            "{base_name}ListJSONAPI".format(base_name=schema.__name__),
            data=(List[object_jsonapi_schema], ...),
            __base__=JSONAPIResultDetailSchema,
        )
        self._resp_schema_list: Type[BaseModel] = list_jsonapi_schema

        # todo: check for any collection except string
        if isinstance(self._path, list):
            for i_path in self._path:
                self._add_routers(i_path)
        else:
            self._add_routers(self._path)

    def _add_routers(self, path: str):
        """Add new router."""
        error_responses: Optional[JSON_API_RESPONSE_TYPE] = {
            400: {"model": ExceptionResponseSchema},
            401: {"model": ExceptionResponseSchema},
            404: {"model": ExceptionResponseSchema},
            500: {"model": ExceptionResponseSchema},
        }
        if hasattr(self.class_list, "get"):
            # Добавляем в APIRouter API с выгрузкой списка элементов данного ресурса
            self._routers.get(
                path,
                tags=self._tags,
                response_model=self._resp_schema_list,
                responses=error_responses,
                summary=f"Get list of `{self._type}` objects",
            )(
                # Оборачиваем декоратором, который создаст сигнатуру функции для FastAPI
                get_list_jsonapi(
                    schema=self._schema,
                    type_=self._type,
                    schema_resp=self._resp_schema_list,
                    model=self._model,
                    engine=self._engine,
                )(
                    self.class_list.get
                )
            )

        if hasattr(self.class_list, "post"):
            self._routers.post(
                path,
                tags=self._tags,
                response_model=self._resp_schema_detail,
                responses=error_responses,
                summary=f"Create object `{self._type}`"

            )(
                post_list_jsonapi(
                    schema=self._schema,
                    schema_in=self._schema_in_post,
                    type_=self._type,
                    schema_resp=self._resp_schema_detail,
                    model=self._model,
                    engine=self._engine,
                )(self.class_list.post)
            )

        if hasattr(self.class_list, "delete"):
            self._routers.delete(
                path,
                tags=self._tags,
                summary=f"Delete list objects of type `{self._type}`"
            )(
                delete_list_jsonapi(
                    schema=self._schema,
                    model=self._model,
                    engine=self._engine,
                )(
                    self.class_list.delete
                )
            )

        if hasattr(self.class_detail, "get"):
            self._routers.get(
                path + "/{obj_id}",
                tags=self._tags,
                response_model=self._resp_schema_detail,
                responses=error_responses,
                summary=f"Get object `{self._type}` by id"
            )(
                get_detail_jsonapi(
                    schema=self._schema,
                    type_=self._type,
                    schema_resp=self._resp_schema_detail,
                    model=self._model,
                    engine=self._engine,
                )(
                    self.class_detail.get
                )
            )

        if hasattr(self.class_detail, "patch"):
            self._routers.patch(
                path + "/{obj_id}",
                tags=self._tags,
                response_model=self._resp_schema_detail,
                responses=error_responses,
                summary=f"Update object `{self._type}` by id"
            )(
                patch_detail_jsonapi(
                    schema=self._schema,
                    schema_in=self._schema_in_patch,
                    type_=self._type,
                    schema_resp=self._resp_schema_detail,
                    model=self._model,
                    engine=self._engine,
                )(
                    self.class_detail.patch
                )
            )

        if hasattr(self.class_detail, "delete"):
            self._routers.delete(
                path + "/{obj_id}",
                tags=self._tags,
                summary=f"Delete object of type `{self._type}`"
            )(
                delete_detail_jsonapi(
                    schema=self._schema,
                    model=self._model,
                    engine=self._engine,
                )(
                    self.class_detail.delete
                )
            )
