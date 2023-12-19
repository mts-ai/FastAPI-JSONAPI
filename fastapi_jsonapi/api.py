"""JSON API router class."""
from enum import Enum, auto
from inspect import Parameter, Signature, signature
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Dict,
    Iterable,
    List,
    Literal,
    Optional,
    Type,
    TypeVar,
    Union,
)

from fastapi import APIRouter, Body, Path, Query, Request, status
from pydantic import BaseModel as PydanticBaseModel

from fastapi_jsonapi.data_typing import TypeModel
from fastapi_jsonapi.exceptions import ExceptionResponseSchema
from fastapi_jsonapi.schema_base import BaseModel
from fastapi_jsonapi.schema_builder import SchemaBuilder
from fastapi_jsonapi.signature import create_additional_query_params
from fastapi_jsonapi.utils.dependency_helper import DependencyHelper
from fastapi_jsonapi.views.utils import (
    HTTPMethod,
    HTTPMethodConfig,
)

if TYPE_CHECKING:
    from fastapi_jsonapi.views.detail_view import DetailViewBase
    from fastapi_jsonapi.views.list_view import ListViewBase
    from fastapi_jsonapi.views.view_base import ViewBase

JSON_API_RESPONSE_TYPE = Dict[Union[int, str], Dict[str, Any]]

JSONAPIObjectSchemaType = TypeVar("JSONAPIObjectSchemaType", bound=PydanticBaseModel)

not_passed = object()


class ViewMethods(str, Enum):
    GET_LIST = auto()
    POST = auto()
    DELETE_LIST = auto()
    GET = auto()
    DELETE = auto()
    PATCH = auto()


class RoutersJSONAPI:
    """
    API Router interface for JSON API endpoints in web-services.
    """

    # xxx: store in app, not in routers!
    all_jsonapi_routers: ClassVar[Dict[str, "RoutersJSONAPI"]] = {}
    Methods = ViewMethods
    DEFAULT_METHODS = tuple(str(method) for method in ViewMethods)

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
        methods: Iterable[str] = (),
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
        self.type_: str = resource_type
        self._schema: Type[BaseModel] = schema
        self.schema_list: Type[BaseModel] = schema
        self.model: Type[TypeModel] = model
        self.schema_detail = schema
        # tuple and not set, so ordering is persisted
        self.methods = tuple(methods) or self.DEFAULT_METHODS

        if self.type_ in self.all_jsonapi_routers:
            msg = f"Resource type {self.type_!r} already registered"
            raise ValueError(msg)
        self.all_jsonapi_routers[self.type_] = self

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
        # we need to save post_data and patch_data
        # and set dependency `data` as `embed=True`
        # because if there's more than one Body dependency,
        # FastAPI makes them all `embed=True` and validation breaks!
        # doc url
        # https://fastapi.tiangolo.com/tutorial/body-multiple-params/#embed-a-single-body-parameter
        # code:
        # https://github.com/tiangolo/fastapi/blob/831b5d5402a65ee9f415670f4116522c8e874ed3/fastapi/dependencies/utils.py#L768
        self.schema_in_post = dto.schema_in_post
        self.schema_in_post_data = dto.schema_in_post_data
        self.schema_in_patch = dto.schema_in_patch
        self.schema_in_patch_data = dto.schema_in_patch_data
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

    def get_endpoint_name(
        self,
        action: Literal["get", "create", "update", "delete"],
        kind: Literal["list", "detail"],
    ):
        """
        Generate view name

        :param action
        :param kind: list / detail
        :return:
        """
        return f"{action}_{self.type_}_{kind}"

    def _register_get_resource_list(self, path: str):
        list_response_example = {
            status.HTTP_200_OK: {"model": self.list_response_schema},
        }
        self._router.add_api_route(
            path=path,
            tags=self._tags,
            responses=list_response_example | self.default_error_responses,
            methods=["GET"],
            summary=f"Get list of `{self.type_}` objects",
            endpoint=self._create_get_resource_list_view(),
            name=self.get_endpoint_name("get", "list"),
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
            summary=f"Create object `{self.type_}`",
            status_code=status.HTTP_201_CREATED,
            endpoint=self._create_post_resource_list_view(),
            name=self.get_endpoint_name("create", "list"),
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
            summary=f"Delete objects `{self.type_}` by filters",
            endpoint=self._create_delete_resource_list_view(),
            name=self.get_endpoint_name("delete", "list"),
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
            summary=f"Get object `{self.type_}` by id",
            endpoint=self._create_get_resource_detail_view(),
            name=self.get_endpoint_name("get", "detail"),
        )

    def _register_patch_resource_detail(self, path: str):
        update_response_example = {
            status.HTTP_200_OK: {"model": self.detail_response_schema},
        }
        self._router.add_api_route(
            # TODO: variable path param name (set default name on DetailView class)
            # TODO: trailing slash (optional)
            path=path + "/{obj_id}",
            tags=self._tags,
            responses=update_response_example | self.default_error_responses,
            methods=["PATCH"],
            summary=f"Patch object `{self.type_}` by id",
            endpoint=self._create_patch_resource_detail_view(),
            name=self.get_endpoint_name("update", "detail"),
        )

    def _register_delete_resource_detail(self, path: str):
        delete_response_example = {
            status.HTTP_204_NO_CONTENT: {
                "description": "If a server is able to delete the resource,"
                " the server MUST return a result with no data",
            },
        }
        self._router.add_api_route(
            # TODO: variable path param name (set default name on DetailView class)
            # TODO: trailing slash (optional)
            path=path + "/{obj_id}",
            tags=self._tags,
            responses=delete_response_example | self.default_error_responses,
            methods=["DELETE"],
            summary=f"Delete object `{self.type_}` by id",
            endpoint=self._create_delete_resource_detail_view(),
            name=self.get_endpoint_name("delete", "detail"),
            status_code=status.HTTP_204_NO_CONTENT,
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

    def _update_signature_for_resource_list_view(
        self,
        wrapper: Callable[..., Any],
        additional_dependency_params: Iterable[Parameter] = (),
    ) -> Signature:
        sig = signature(wrapper)
        params, tail_params = self._get_separated_params(sig)

        filter_params, include_params = create_additional_query_params(schema=self.schema_detail)

        extra_params = []
        extra_params.extend(self._create_pagination_query_params())
        extra_params.extend(filter_params)
        extra_params.append(self._create_filters_query_dependency_param())
        extra_params.append(self._create_sort_query_dependency_param())
        extra_params.extend(include_params)

        return sig.replace(parameters=params + extra_params + list(additional_dependency_params) + tail_params)

    def _update_signature_for_resource_detail_view(
        self,
        wrapper: Callable[..., Any],
        additional_dependency_params: Iterable[Parameter] = (),
    ) -> Signature:
        sig = signature(wrapper)
        params, tail_params = self._get_separated_params(sig)

        _, include_params = create_additional_query_params(schema=self.schema_detail)

        return sig.replace(parameters=params + include_params + list(additional_dependency_params) + tail_params)

    def _create_dependency_params_from_pydantic_model(self, model_class: Type[BaseModel]) -> List[Parameter]:
        return [
            Parameter(
                name=field_name,
                kind=Parameter.POSITIONAL_OR_KEYWORD,
                annotation=field_info.outer_type_,
                default=field_info.default,
            )
            for field_name, field_info in model_class.__fields__.items()
        ]

    def _update_method_config(self, view: Type["ViewBase"], method: HTTPMethod) -> HTTPMethodConfig:
        target_config = view.method_dependencies.get(method) or HTTPMethodConfig()
        common_config = view.method_dependencies.get(HTTPMethod.ALL) or HTTPMethodConfig()

        dependencies_model = target_config.dependencies or common_config.dependencies

        same_type = target_config.dependencies is common_config.dependencies
        if not same_type and all([target_config.dependencies, common_config.dependencies]):
            dependencies_model = type(
                f"{view.__name__}{method.name.title()}MethodDependencyModel",
                (
                    common_config.dependencies,
                    target_config.dependencies,
                ),
                {},
            )

        new_method_config = HTTPMethodConfig(
            dependencies=dependencies_model,
            prepare_data_layer_kwargs=target_config.handler or common_config.handler,
        )
        view.method_dependencies[method] = new_method_config

        return new_method_config

    def _update_method_config_and_get_dependency_params(
        self,
        view: Type["ViewBase"],
        method: HTTPMethod,
    ) -> List[Parameter]:
        method_config = self._update_method_config(view, method)

        if method_config.dependencies is None:
            return []

        return self._create_dependency_params_from_pydantic_model(method_config.dependencies)

    def prepare_dependencies_handler_signature(
        self,
        custom_handler: Callable[..., Any],
        method_config: HTTPMethodConfig,
    ) -> Signature:
        sig = signature(custom_handler)

        additional_dependency_params = []
        if method_config.dependencies is not None:
            additional_dependency_params = self._create_dependency_params_from_pydantic_model(
                model_class=method_config.dependencies,
            )

        params, tail_params = self._get_separated_params(sig)

        return sig.replace(parameters=params + list(additional_dependency_params) + tail_params)

    async def handle_view_dependencies(
        self,
        request: Request,
        view_cls: Type["ViewBase"],
        method: HTTPMethod,
    ) -> Dict[str, Any]:
        """
        Combines all dependencies (prepared) and returns them as list

        Consider method config is already prepared for generic views
        Reuse the same config for atomic operations

        :param request:
        :param view_cls:
        :param method:
        :return:
        """
        method_config: HTTPMethodConfig = view_cls.method_dependencies[method]

        def handle_dependencies(**dep_kwargs):
            return dep_kwargs

        handle_dependencies.__signature__ = self.prepare_dependencies_handler_signature(
            custom_handler=handle_dependencies,
            method_config=method_config,
        )

        dep_helper = DependencyHelper(request=request)
        dependencies_result: Dict[str, Any] = await dep_helper.run(handle_dependencies)
        return dependencies_result

    def _create_get_resource_list_view(self):
        """
        Create wrapper for GET list (get objects list)

        :return:
        """

        async def wrapper(request: Request, **extra_view_deps):
            resource = self.list_view_resource(
                request=request,
                jsonapi=self,
            )

            response = await resource.handle_get_resource_list(**extra_view_deps)
            return response

        additional_dependency_params = self._update_method_config_and_get_dependency_params(
            self.list_view_resource,
            HTTPMethod.GET,
        )
        wrapper.__signature__ = self._update_signature_for_resource_list_view(
            wrapper,
            additional_dependency_params=additional_dependency_params,
        )
        return wrapper

    def _create_post_resource_list_view(self):
        """
        Create wrapper for POST list (create a new object)

        :return:
        """
        # `data` as embed Body param
        schema_in = self.schema_in_post_data

        async def wrapper(
            request: Request,
            data: schema_in = Body(embed=True),
            **extra_view_deps,
        ):
            resource = self.list_view_resource(
                request=request,
                jsonapi=self,
            )

            response = await resource.handle_post_resource_list(
                data_create=data,
                **extra_view_deps,
            )
            return response

        additional_dependency_params = self._update_method_config_and_get_dependency_params(
            self.list_view_resource,
            HTTPMethod.POST,
        )

        # POST request returns result as for detail view
        wrapper.__signature__ = self._update_signature_for_resource_detail_view(
            wrapper,
            additional_dependency_params=additional_dependency_params,
        )
        return wrapper

    def _create_delete_resource_list_view(self):
        """
        Create wrapper for DELETE list (delete objects)

        :return:
        """

        async def wrapper(request: Request, **extra_view_deps):
            resource = self.list_view_resource(
                request=request,
                jsonapi=self,
            )

            response = await resource.handle_delete_resource_list(**extra_view_deps)
            return response

        additional_dependency_params = self._update_method_config_and_get_dependency_params(
            self.list_view_resource,
            HTTPMethod.DELETE,
        )

        wrapper.__signature__ = self._update_signature_for_resource_list_view(
            wrapper,
            additional_dependency_params=additional_dependency_params,
        )
        return wrapper

    def _create_get_resource_detail_view(self):
        """
        Create wrapper for GET detail (get object by id)

        :return:
        """

        # TODO:
        #  - custom path param name (set default name on DetailView class)
        #  - custom type for obj id (get type from DetailView class)
        async def wrapper(request: Request, obj_id: str = Path(...), **extra_view_deps):
            resource = self.detail_view_resource(
                request=request,
                jsonapi=self,
            )

            # TODO: pass obj_id as kwarg (get name from DetailView class)
            response = await resource.handle_get_resource_detail(obj_id, **extra_view_deps)
            return response

        additional_dependency_params = self._update_method_config_and_get_dependency_params(
            self.detail_view_resource,
            HTTPMethod.GET,
        )

        wrapper.__signature__ = self._update_signature_for_resource_detail_view(
            wrapper,
            additional_dependency_params=additional_dependency_params,
        )
        return wrapper

    def _create_patch_resource_detail_view(self):
        """
        Create wrapper for PATCH detail (patch object by id)

        :return:
        """
        # `data` as embed Body param
        schema_in = self.schema_in_patch_data

        async def wrapper(
            request: Request,
            data: schema_in = Body(embed=True),
            obj_id: str = Path(...),
            **extra_view_deps,
        ):
            resource = self.detail_view_resource(
                request=request,
                jsonapi=self,
            )

            # TODO: pass obj_id as kwarg (get name from DetailView class)
            response = await resource.handle_update_resource(
                obj_id=obj_id,
                data_update=data,
                **extra_view_deps,
            )
            return response

        additional_dependency_params = self._update_method_config_and_get_dependency_params(
            self.detail_view_resource,
            HTTPMethod.PATCH,
        )

        wrapper.__signature__ = self._update_signature_for_resource_detail_view(
            wrapper,
            additional_dependency_params=additional_dependency_params,
        )
        return wrapper

    def _create_delete_resource_detail_view(self):
        """
        Create wrapper for DELETE detail (delete object by id)

        :return:
        """

        async def wrapper(
            request: Request,
            obj_id: str = Path(...),
            **extra_view_deps,
        ):
            resource = self.detail_view_resource(
                request=request,
                jsonapi=self,
            )

            # TODO: pass obj_id as kwarg (get name from DetailView class)
            response = await resource.handle_delete_resource(obj_id=obj_id, **extra_view_deps)
            return response

        additional_dependency_params = self._update_method_config_and_get_dependency_params(
            self.detail_view_resource,
            HTTPMethod.DELETE,
        )

        wrapper.__signature__ = self._update_signature_for_resource_detail_view(
            wrapper,
            additional_dependency_params=additional_dependency_params,
        )

        return wrapper

    def _register_views(self, path: str):
        """
        Register wrapper views

        :param path:
        :return:
        """
        methods_map: Dict[Union[str, ViewMethods], Callable[[str], None]] = {
            ViewMethods.GET_LIST: self._register_get_resource_list,
            ViewMethods.POST: self._register_post_resource_list,
            ViewMethods.DELETE_LIST: self._register_delete_resource_list,
            ViewMethods.GET: self._register_get_resource_detail,
            ViewMethods.PATCH: self._register_patch_resource_detail,
            ViewMethods.DELETE: self._register_delete_resource_detail,
        }
        # patch for Python < 3.11
        for key, value in list(methods_map.items()):
            methods_map[str(key)] = value

        for method in self.methods:
            # `to str` so Python < 3.11 is supported
            register = methods_map[str(method)]
            register(path)
