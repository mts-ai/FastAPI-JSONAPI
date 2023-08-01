"""JSON API router class."""
from inspect import Parameter, Signature, signature
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)

from fastapi import APIRouter, Path, Query, Request, status
from pydantic import BaseModel as PydanticBaseModel

from fastapi_jsonapi.data_layers.data_typing import TypeModel
from fastapi_jsonapi.exceptions import ExceptionResponseSchema
from fastapi_jsonapi.schema_base import BaseModel
from fastapi_jsonapi.schema_builder import SchemaBuilder
from fastapi_jsonapi.signature import create_additional_query_params
from fastapi_jsonapi.utils.dependency_helper import DependencyHelper

if TYPE_CHECKING:
    from fastapi_jsonapi.views.detail_view import DetailViewBase
    from fastapi_jsonapi.views.list_view import ListViewBase

JSON_API_RESPONSE_TYPE = Dict[Union[int, str], Dict[str, Any]]

JSONAPIObjectSchemaType = TypeVar("JSONAPIObjectSchemaType", bound=PydanticBaseModel)

not_passed = object()


class RoutersJSONAPI:
    """API Router interface for JSON API endpoints in web-services."""

    def __init__(
        self,
        router: APIRouter,
        path: Union[str, List[str]],
        tags: List[str],
        class_list: Type["ListViewBase"],
        class_detail: Type["DetailViewBase"],
        model: Type[TypeModel],
        schema: Type[BaseModel],
        resource_type: str,
        schema_in_post: Optional[Type[BaseModel]] = None,
        schema_in_patch: Optional[Type[BaseModel]] = None,
        pagination_default_size: Optional[int] = 25,
        pagination_default_number: Optional[int] = 1,
        pagination_default_offset: Optional[int] = None,
        pagination_default_limit: Optional[int] = None,
    ) -> None:
        """
        Initialize router items.

        :param router: APIRouter from FastAPI
        :param path: path prefix, for example `/users`
        :param tags: swagger tags
        :param class_detail: detail view class
        :param class_list: list view class
        :param model: SQLA / Tortoise / any other ORM model
        :param schema: full object schema for this resource
        :param resource_type: `resource type` (JSON:API required)
        :param schema_in_post: schema for POST - custom schema to use instead of `schema`
        :param schema_in_patch: schema for PATCH - custom schema to use instead of `schema`

        # default pagination params for swagger
        :param pagination_default_size: `page[size]`
                default swagger param. page/size pagination, used with `page[number]`
        :param pagination_default_number: `page[number]`
                default swagger param. page/size pagination, used with `page[size]`
        :param pagination_default_offset: `page[offset]`
                default swagger param. limit/offset pagination, used with `page[limit]`
        :param pagination_default_limit: `page[limit]`
                default swagger param. limit/offset pagination, used with `page[offset]`
        """
        self._router: APIRouter = router
        self._path: Union[str, List[str]] = path
        self._tags: List[str] = tags
        self.detail_views = None
        self.list_views = None
        self.detail_view_resource: Type["DetailViewBase"] = class_detail
        self.list_view_resource: Type["ListViewBase"] = class_list
        self._type: str = resource_type
        self._schema: Type[BaseModel] = schema
        self.schema_list: Type[BaseModel] = schema
        self.model: Type[TypeModel] = model
        self.schema_detail = schema

        self.pagination_default_size: Optional[int] = pagination_default_size
        self.pagination_default_number: Optional[int] = pagination_default_number
        self.pagination_default_offset: Optional[int] = pagination_default_offset
        self.pagination_default_limit: Optional[int] = pagination_default_limit
        self.schema_builder = SchemaBuilder(resource_type=resource_type)

        dto = self.schema_builder.create_schemas(
            schema=schema,
            schema_in_post=schema_in_post,
            schema_in_patch=schema_in_patch,
        )
        self._schema_in_post = dto.schema_in_post
        self._schema_in_patch = dto.schema_in_patch
        self.detail_response_schema = dto.detail_response_schema
        self.list_response_schema = dto.list_response_schema

        self._prepare_responses()
        self._create_and_register_generic_views()

    def _prepare_responses(self):
        self.default_error_responses: JSON_API_RESPONSE_TYPE = {
            status.HTTP_400_BAD_REQUEST: {"model": ExceptionResponseSchema},
            status.HTTP_401_UNAUTHORIZED: {"model": ExceptionResponseSchema},
            status.HTTP_404_NOT_FOUND: {"model": ExceptionResponseSchema},
            status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ExceptionResponseSchema},
        }

    def _create_and_register_generic_views(self):
        if isinstance(self._path, Iterable) and not isinstance(self._path, (str, bytes)):
            for i_path in self._path:
                self._register_views(i_path)
        else:
            self._register_views(self._path)

    def _register_get_resource_list(self, path: str):
        list_response_example = {
            status.HTTP_200_OK: {"model": self.list_response_schema},
        }
        self._router.add_api_route(
            path=path,
            tags=self._tags,
            responses=list_response_example | self.default_error_responses,
            methods=["GET"],
            summary=f"Get list of `{self._type}` objects",
            endpoint=self._create_get_resource_list_view(),
        )

    def _register_post_resource_list(self, path: str):
        create_resource_response_example = {
            status.HTTP_201_CREATED: {"model": self.detail_response_schema},
        }
        self._router.add_api_route(
            path=path,
            tags=self._tags,
            responses=create_resource_response_example | self.default_error_responses,
            methods=["POST"],
            summary=f"Create object `{self._type}`",
            status_code=status.HTTP_201_CREATED,
            endpoint=self._create_post_resource_list_view(),
        )

    def _register_delete_resource_list(self, path: str):
        detail_response_example = {
            status.HTTP_200_OK: {"model": self.detail_response_schema},
        }
        self._router.add_api_route(
            path=path,
            tags=self._tags,
            responses=detail_response_example | self.default_error_responses,
            methods=["DELETE"],
            summary=f"Delete objects `{self._type}` by filters",
            endpoint=self._create_delete_resource_list_view(),
        )

    def _register_get_resource_detail(self, path: str):
        detail_response_example = {
            status.HTTP_200_OK: {"model": self.detail_response_schema},
        }
        self._router.add_api_route(
            # TODO: variable path param name (set default name on DetailView class)
            # TODO: trailing slash (optional)
            path=path + "/{obj_id}",
            tags=self._tags,
            responses=detail_response_example | self.default_error_responses,
            methods=["GET"],
            summary=f"Get object `{self._type}` by id",
            endpoint=self._create_get_resource_detail_view(),
        )

    def _register_patch_resource_detail(self, path: str):
        detail_response_example = {
            status.HTTP_200_OK: {"model": self.detail_response_schema},
        }
        self._router.add_api_route(
            # TODO: variable path param name (set default name on DetailView class)
            # TODO: trailing slash (optional)
            path=path + "/{obj_id}",
            tags=self._tags,
            responses=detail_response_example | self.default_error_responses,
            methods=["PATCH"],
            summary=f"Patch object `{self._type}` by id",
            endpoint=self._create_patch_resource_detail_view(),
        )

    def _register_delete_resource_detail(self, path: str):
        detail_response_example = {
            status.HTTP_200_OK: {"model": self.detail_response_schema},
        }
        self._router.add_api_route(
            # TODO: variable path param name (set default name on DetailView class)
            # TODO: trailing slash (optional)
            path=path + "/{obj_id}",
            tags=self._tags,
            responses=detail_response_example | self.default_error_responses,
            methods=["DELETE"],
            summary=f"Delete object `{self._type}` by id",
            endpoint=self._create_delete_resource_detail_view(),
        )

    def _create_pagination_query_params(self) -> List[Parameter]:
        size = Query(self.pagination_default_size, alias="page[size]", title="pagination_page_size")
        number = Query(self.pagination_default_number, alias="page[number]", title="pagination_page_number")
        offset = Query(self.pagination_default_offset, alias="page[offset]", title="pagination_page_offset")
        limit = Query(self.pagination_default_limit, alias="page[limit]", title="pagination_page_limit")

        params = []

        for q_param in (
            size,
            number,
            offset,
            limit,
        ):
            params.append(
                Parameter(
                    # name doesn't really matter here
                    name=q_param.title,
                    kind=Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=Optional[int],
                    default=q_param,
                ),
            )

        return params

    @classmethod
    def _create_filters_query_dependency_param(cls):
        filters_list = Query(
            None,
            alias="filter",
            description="[Filtering docs](https://fastapi-jsonapi.readthedocs.io/en/latest/filtering.html)"
            "\nExamples:\n* filter for timestamp interval: "
            '`[{"name": "timestamp", "op": "ge", "val": "2020-07-16T11:35:33.383"},'
            '{"name": "timestamp", "op": "le", "val": "2020-07-21T11:35:33.383"}]`',
        )
        return Parameter(
            name="filters_list",
            kind=Parameter.POSITIONAL_OR_KEYWORD,
            annotation=Optional[str],
            default=filters_list,
        )

    @classmethod
    def _create_sort_query_dependency_param(cls):
        sort = Query(
            None,
            alias="sort",
            description="[Sorting docs](https://fastapi-jsonapi.readthedocs.io/en/latest/sorting.html)"
            "\nExamples:\n* `email` - sort by email ASC\n* `-email` - sort by email DESC"
            "\n* `created_at,-email` - sort by created_at ASC and by email DESC",
        )
        return Parameter(
            name="sort",
            kind=Parameter.POSITIONAL_OR_KEYWORD,
            annotation=Optional[str],
            default=sort,
        )

    @classmethod
    def _get_separated_params(cls, sig: Signature):
        """
        Separate params, tail params, skip **kwargs

        :param sig:
        :return:
        """
        params = []
        tail_params = []

        for name, param in sig.parameters.items():
            if param.kind is Parameter.VAR_KEYWORD:
                # skip **kwargs for spec
                continue

            if param.kind is Parameter.KEYWORD_ONLY:
                tail_params.append(param)
            else:
                params.append(param)

        return params, tail_params

    def _update_signature_for_resource_list_view(self, wrapper: Callable[..., Any]) -> Signature:
        sig = signature(wrapper)
        params, tail_params = self._get_separated_params(sig)

        filter_params, include_params = create_additional_query_params(schema=self.schema_detail)

        extra_params = []
        extra_params.extend(self._create_pagination_query_params())
        extra_params.extend(filter_params)
        extra_params.append(self._create_filters_query_dependency_param())
        extra_params.append(self._create_sort_query_dependency_param())
        extra_params.extend(include_params)

        return sig.replace(parameters=params + extra_params + tail_params)

    def _update_signature_for_resource_detail_view(self, wrapper: Callable[..., Any]) -> Signature:
        sig = signature(wrapper)
        params, tail_params = self._get_separated_params(sig)

        _, include_params = create_additional_query_params(schema=self.schema_detail)

        return sig.replace(parameters=params + include_params + tail_params)

    def _create_get_resource_list_view(self):
        """
        Create wrapper for GET list (get objects list)
        :return:
        """

        async def wrapper(request: Request, **kwargs):
            resource = self.list_view_resource(
                request=request,
                jsonapi=self,
            )
            await DependencyHelper(request=request).run(resource.init_dependencies)

            response = await resource.get_resource_list_result()
            return response

        wrapper.__signature__ = self._update_signature_for_resource_list_view(wrapper)
        return wrapper

    def _create_post_resource_list_view(self):
        """
        Create wrapper for POST list (create a new object)

        :return:
        """
        schema_in = self._schema_in_post

        async def wrapper(request: Request, data_create: schema_in, **kwargs):
            resource = self.list_view_resource(
                request=request,
                jsonapi=self,
            )
            await DependencyHelper(request=request).run(resource.init_dependencies)

            response = await resource.post_resource_list_result(data_create=data_create)
            return response

        # POST request returns result as for detail view
        wrapper.__signature__ = self._update_signature_for_resource_detail_view(wrapper)
        return wrapper

    def _create_delete_resource_list_view(self):
        """
        Create wrapper for DELETE list (delete objects)

        :return:
        """

        async def wrapper(request: Request, **kwargs):
            resource = self.list_view_resource(
                request=request,
                jsonapi=self,
            )
            await DependencyHelper(request=request).run(resource.init_dependencies)

            response = await resource.delete_resource_list_result()
            return response

        wrapper.__signature__ = self._update_signature_for_resource_list_view(wrapper)
        return wrapper

    def _create_get_resource_detail_view(self):
        """
        Create wrapper for GET detail (get object by id)

        :return:
        """

        # TODO:
        #  - custom path param name (set default name on DetailView class)
        #  - custom type for obj id (get type from DetailView class)
        async def wrapper(request: Request, obj_id: str = Path(...), **kwargs):
            resource = self.detail_view_resource(
                request=request,
                jsonapi=self,
            )
            await DependencyHelper(request=request).run(resource.init_dependencies)

            # TODO: pass obj_id as kwarg (get name from DetailView class)
            response = await resource.get_resource_detail_result(obj_id)
            return response

        wrapper.__signature__ = self._update_signature_for_resource_detail_view(wrapper)
        return wrapper

    def _create_patch_resource_detail_view(self):
        """
        Create wrapper for PATCH detail (patch object by id)

        :return:
        """
        schema_in = self._schema_in_patch

        async def wrapper(
            request: Request,
            data_update: schema_in,
            obj_id: str = Path(...),
            **kwargs,
        ):
            resource = self.detail_view_resource(
                request=request,
                jsonapi=self,
            )
            await DependencyHelper(request=request).run(resource.init_dependencies)

            # TODO: pass obj_id as kwarg (get name from DetailView class)
            response = await resource.update_resource_result(
                obj_id=obj_id,
                data_update=data_update.data,
            )
            return response

        wrapper.__signature__ = self._update_signature_for_resource_detail_view(wrapper)
        return wrapper

    def _create_delete_resource_detail_view(self):
        """
        Create wrapper for DELETE detail (delete object by id)

        :return:
        """

        async def wrapper(
            request: Request,
            obj_id: str = Path(...),
            **kwargs,
        ):
            resource = self.detail_view_resource(
                request=request,
                jsonapi=self,
            )
            await DependencyHelper(request=request).run(resource.init_dependencies)

            # TODO: pass obj_id as kwarg (get name from DetailView class)
            response = await resource.delete_resource_result(
                obj_id=obj_id,
            )
            return response

        wrapper.__signature__ = self._update_signature_for_resource_detail_view(wrapper)
        return wrapper

    def _register_views(self, path: str):
        """
        Register wrapper views

        :param path:
        :return:
        """
        self._register_get_resource_list(path)
        self._register_post_resource_list(path)
        self._register_delete_resource_list(path)

        self._register_get_resource_detail(path)
        self._register_patch_resource_detail(path)
        self._register_delete_resource_detail(path)
