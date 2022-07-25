"""JSON API router class."""

from typing import (
    Any,
    Dict,
    List,
    Optional,
    Type,
    Union,
)

import pydantic
from fastapi import APIRouter
from pydantic import BaseModel, Field

from fastapi_rest_jsonapi.exceptions import ExceptionResponseSchema
from fastapi_rest_jsonapi.methods import (
    delete_detail_jsonapi,
    get_detail_jsonapi,
    get_list_jsonapi,
    patch_detail_jsonapi,
    post_list_jsonapi,
)
from fastapi_rest_jsonapi.schema import BasePatchJSONAPISchema, BasePostJSONAPISchema, JSONAPIObjectSchema, \
    JSONAPIResultDetailSchema

JSON_API_RESPONSE_TYPE = Optional[Dict[Union[int, str], Dict[str, Any]]]


class RoutersJSONAPI(object):
    """API Router interface for JSON API endpoints in web-services."""

    def __init__(  # noqa: WPS211
        self,
        routers: APIRouter,
        path: Union[str, List[str]],
        tags: List[str],
        class_detail: Any,
        class_list: Any,
        schema: Type[BaseModel],
        type_resource: str,
        schema_in_patch: Type[BaseModel],
        schema_in_post: Type[BaseModel],
    ) -> None:
        """Initialize router items."""
        self._routers: APIRouter = routers
        self._path: Union[str, List[str]] = path
        self._tags: List[str] = tags
        self.class_detail: Any = class_detail
        self.class_list: Any = class_list
        self._type: str = type_resource
        self._schema: Type[BaseModel] = schema

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
            self._routers.get(path, tags=self._tags, response_model=self._resp_schema_list, responses=error_responses,)(
                get_list_jsonapi(schema=self._schema, type_=self._type, schema_resp=self._resp_schema_list)(
                    self.class_list.get
                )
            )

        if hasattr(self.class_list, "post"):
            self._routers.post(
                path,
                tags=self._tags,
                response_model=self._resp_schema_detail,
                responses=error_responses,
            )(
                post_list_jsonapi(
                    schema=self._schema,
                    schema_in=self._schema_in_post,
                    type_=self._type,
                    schema_resp=self._resp_schema_detail,
                )(self.class_list.post)
            )

        if hasattr(self.class_detail, "get"):
            self._routers.get(
                path + "/{obj_id}",
                tags=self._tags,
                response_model=self._resp_schema_detail,
                responses=error_responses,
            )(
                get_detail_jsonapi(schema=self._schema, type_=self._type, schema_resp=self._resp_schema_detail)(
                    self.class_detail.get
                )
            )

        if hasattr(self.class_detail, "patch"):
            self._routers.patch(
                path + "/{obj_id}",
                tags=self._tags,
                response_model=self._resp_schema_detail,
                responses=error_responses,
            )(
                patch_detail_jsonapi(
                    schema=self._schema,
                    schema_in=self._schema_in_patch,
                    type_=self._type,
                    schema_resp=self._resp_schema_detail,
                )(self.class_detail.patch)
            )

        if hasattr(self.class_detail, "delete"):
            self._routers.delete(
                path + "/{obj_id}",
                tags=self._tags,
            )(delete_detail_jsonapi(schema=self._schema)(self.class_detail.delete))
