"""JSON API router class."""
from dataclasses import dataclass
from inspect import Parameter, Signature, signature
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
    Type,
    Union,
)

import pydantic
from fastapi import APIRouter, Path, Query, Request, status
from pydantic import BaseConfig
from pydantic.fields import ModelField

from fastapi_jsonapi.data_layers.data_typing import TypeModel, TypeSchema
from fastapi_jsonapi.exceptions import ExceptionResponseSchema
from fastapi_jsonapi.methods import (
    delete_detail_jsonapi,
    delete_list_jsonapi,
    patch_detail_jsonapi,
    post_list_jsonapi,
)
from fastapi_jsonapi.schema import (
    BaseJSONAPIRelationshipDataToManySchema,
    BaseJSONAPIRelationshipDataToOneSchema,
    BaseJSONAPIRelationshipSchema,
    BaseJSONAPIResultSchema,
    BasePatchJSONAPISchema,
    BasePostJSONAPISchema,
    JSONAPIObjectSchema,
    JSONAPIResultDetailSchema,
    JSONAPIResultListSchema,
)
from fastapi_jsonapi.schema_base import BaseModel, Field, RelationshipInfo, registry
from fastapi_jsonapi.signature import create_additional_query_params
from fastapi_jsonapi.splitter import SPLIT_REL
from fastapi_jsonapi.utils.dependency_helper import DependencyHelper

if TYPE_CHECKING:
    from fastapi_jsonapi.views.detail_view import DetailViewBase
    from fastapi_jsonapi.views.list_view import ListViewBase

JSON_API_RESPONSE_TYPE = Dict[Union[int, str], Dict[str, Any]]


not_passed = object()


# todo: when 3.9 support is dropped, return back `slots=True to JSONAPIObjectSchemas dataclass`


@dataclass(frozen=True)
class JSONAPIObjectSchemas:
    attributes_schema: Type[BaseModel]
    relationships_schema: Type[BaseModel]
    object_jsonapi_schema: Type[JSONAPIObjectSchema]
    can_be_included_schemas: Dict[str, Type[JSONAPIObjectSchema]]

    @property
    def included_schemas_list(self) -> List[Type[JSONAPIObjectSchema]]:
        return list(self.can_be_included_schemas.values())


class RoutersJSONAPI:
    """API Router interface for JSON API endpoints in web-services."""

    # IDK if there's a better way than global caches
    # shared between ALL RoutersJSONAPI instances
    object_schemas_cache = {}
    relationship_schema_cache = {}
    related_schemas_cache = {}

    def __init__(
        self,
        router: APIRouter,
        path: Union[str, List[str]],
        tags: List[str],
        class_detail: Type["DetailViewBase"],
        class_list: Type["ListViewBase"],
        schema: Type[BaseModel],
        resource_type: str,
        schema_in_patch: Type[BaseModel],
        schema_in_post: Type[BaseModel],
        model: Type[TypeModel],
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
        :param schema: full object schema for this resource
        :param resource_type: `resource type` (JSON:API required)
        :param schema_in_patch: schema for PATCH
        :param schema_in_post: schema for POST
        :param model: SQLA / Tortoise / etc ORM model

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

        self.default_error_responses: JSON_API_RESPONSE_TYPE = {
            status.HTTP_400_BAD_REQUEST: {"model": ExceptionResponseSchema},
            status.HTTP_401_UNAUTHORIZED: {"model": ExceptionResponseSchema},
            status.HTTP_404_NOT_FOUND: {"model": ExceptionResponseSchema},
            status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ExceptionResponseSchema},
        }

        patch_jsonapi_schema = pydantic.create_model(
            "{base_name}JSONAPI".format(base_name=schema_in_patch.__name__),
            attributes=(schema_in_patch, ...),
            type=(str, Field(default=self._type, description="Resource type")),
            __base__=BasePatchJSONAPISchema,
        )
        self._schema_in_patch_base: Type[BaseModel] = schema_in_patch
        self._schema_in_patch: Type[BaseModel] = patch_jsonapi_schema

        post_jsonapi_schema = pydantic.create_model(
            "{base_name}JSONAPI".format(base_name=schema_in_post.__name__),
            attributes=(schema_in_post, ...),
            type=(str, Field(default=self._type, description="Resource type")),
            __base__=BasePostJSONAPISchema,
        )
        self._schema_in_post_base: Type[BaseModel] = schema_in_post
        self._schema_in_post: Type[BaseModel] = post_jsonapi_schema

        # schemas_in_wip = self.build_schema_in(schema_in=schema_in_post)
        # self._schema_in_post_base: Type[BaseModel] = schemas_in_wip.attributes_schema
        # self._schema_in_post: Type[BaseModel] = schemas_in_wip.object_jsonapi_schema

        object_jsonapi_detail_schema, detail_jsonapi_schema = self.build_detail_schemas(self.schema_detail)
        self.object_jsonapi_detail_schema: Type[JSONAPIObjectSchema] = object_jsonapi_detail_schema
        self.detail_response_schema: Type[JSONAPIResultDetailSchema] = detail_jsonapi_schema

        object_jsonapi_list_schema, list_jsonapi_schema = self.build_list_schemas(self.schema_list)
        self.object_jsonapi_list_schema: Type[JSONAPIObjectSchema] = object_jsonapi_list_schema
        self.list_response_schema: Type[JSONAPIResultListSchema] = list_jsonapi_schema

        if isinstance(self._path, Iterable) and not isinstance(self._path, (str, bytes)):
            for i_path in self._path:
                self._register_views(i_path)
        else:
            self._register_views(self._path)

    def build_schema_in(self, schema_in: Type[BaseModel]):
        schemas = self.create_jsonapi_object_schemas(schema=schema_in)

        return schemas
        base_schema_name = schema_in.__name__
        if base_schema_name.endswith("Schema"):
            base_schema_name = base_schema_name[: -len("Schema")]

        for name, field in (schema_in.__fields__ or {}).items():
            if isinstance(field.field_info.extra.get("relationship"), RelationshipInfo):
                field.field_info.extra["relationship"]
                # schema_name = f"{base_schema_name}To{name.title()}"
                # relationship_schema = self.create_relationship_schema(
                #     name=schema_name,
                #     relationship_info=relationship_info,
                # )
                # relationships_schema_fields[name] = (relationship_schema, None)  # allow to not pass relationships

        post_schema_kwargs = {
            "type": (str, Field(default=self._type, description="Resource type")),
            "attributes": (schema_in, ...),
        }

        # # TODO: pydantic V2 model_config
        # class ConfigOrmMode(BaseConfig):
        #     orm_mode = True
        #
        # # TODO: reuse generic code
        # relationships_schema = pydantic.create_model(
        #     f"{base_schema_name}RelationshipsJSONAPI",
        #     **relationships_schema_fields,
        #     __config__=ConfigOrmMode,
        # )
        #
        # print(relationships_schema)

        # if relationships_schema_fields:
        #     # allow not to pass relationships
        #     post_schema_kwargs.update(relationships=(relationships_schema, None))

        post_jsonapi_schema = pydantic.create_model(
            "{base_name}JSONAPI".format(base_name=schema_in.__name__),
            **post_schema_kwargs,
            __base__=BasePostJSONAPISchema,
        )

        return post_jsonapi_schema

    def _build_schema(
        self,
        base_name: str,
        schema: Type[BaseModel],
        builder: Any,
        includes: Iterable[str] = not_passed,
    ):
        object_schemas = self.create_jsonapi_object_schemas(
            schema=schema,
            base_name=base_name,
            compute_included_schemas=True,
            includes=includes,
        )
        object_jsonapi_schema = object_schemas.object_jsonapi_schema
        response_jsonapi_schema = builder(
            name=base_name,
            object_jsonapi_schema=object_jsonapi_schema,
            includes_schemas=object_schemas.included_schemas_list,
        )
        return object_jsonapi_schema, response_jsonapi_schema

    def build_detail_schemas(
        self,
        schema: Type[BaseModel],
        includes: Iterable[str] = not_passed,
    ) -> Tuple[Type[JSONAPIObjectSchema], Type[JSONAPIResultDetailSchema]]:
        return self._build_schema(
            base_name=f"{schema.__name__}Detail",
            schema=schema,
            builder=self.build_schema_for_detail_result,
            includes=includes,
        )

    def build_list_schemas(
        self,
        schema: Type[BaseModel],
        includes: Iterable[str] = not_passed,
    ) -> Tuple[Type[JSONAPIObjectSchema], Type[JSONAPIResultListSchema]]:
        return self._build_schema(
            base_name=f"{schema.__name__}List",
            schema=schema,
            builder=self.build_schema_for_list_result,
            includes=includes,
        )

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
        Create wrapper for GET list
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

    def _create_get_resource_detail_view(self):
        """
        Create wrapper for GET detail
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

    def _register_views(self, path: str):
        """
        Register wrapper views

        :param path:
        :return:
        """
        error_responses = self.default_error_responses

        detail_response_example = {
            status.HTTP_200_OK: {"model": self.detail_response_schema},
        }
        create_resource_response_example = {
            status.HTTP_201_CREATED: {"model": self.detail_response_schema},
        }
        self._register_get_resource_list(path)
        self._register_get_resource_detail(path)

        if hasattr(self.list_views, "post"):
            self._router.post(
                path,
                tags=self._tags,
                responses=create_resource_response_example | error_responses,
                summary=f"Create object `{self._type}`",
                status_code=status.HTTP_201_CREATED,
            )(
                post_list_jsonapi(
                    schema=self._schema,
                    schema_in=self._schema_in_post,
                    type_=self._type,
                    schema_resp=self.detail_response_schema,
                    model=self.model,
                )(self.list_views.post),
            )

        if hasattr(self.list_views, "delete"):
            self._router.delete(path, tags=self._tags, summary=f"Delete list objects of type `{self._type}`")(
                delete_list_jsonapi(
                    schema=self._schema,
                    model=self.model,
                )(self.list_views.delete),
            )

        if hasattr(self.detail_views, "patch"):
            self._router.patch(
                path + "/{obj_id}",
                tags=self._tags,
                responses=detail_response_example | error_responses,
                summary=f"Update object `{self._type}` by id",
            )(
                patch_detail_jsonapi(
                    schema=self._schema,
                    schema_in=self._schema_in_patch,
                    type_=self._type,
                    schema_resp=self.detail_response_schema,
                    model=self.model,
                )(self.detail_views.patch),
            )

        if hasattr(self.detail_views, "delete"):
            self._router.delete(
                path + "/{obj_id}",
                tags=self._tags,
                summary=f"Delete object of type `{self._type}`",
                status_code=status.HTTP_204_NO_CONTENT,
            )(
                delete_detail_jsonapi(
                    schema=self._schema,
                    model=self.model,
                )(self.detail_views.delete),
            )

    def create_relationship_schema(
        self,
        name: str,
        relationship_info: RelationshipInfo,
    ) -> Type[BaseJSONAPIRelationshipSchema]:
        # TODO: cache?
        if name.endswith("s"):
            # plural to single
            name = name[:-1]

        schema_name = f"{name}RelationshipJSONAPI".format(name=name)
        relationship_schema = pydantic.create_model(
            schema_name,
            id=(str, Field(..., description="Resource object id", example=relationship_info.resource_id_example)),
            type=(str, Field(default=relationship_info.resource_type, description="Resource type")),
            __base__=BaseJSONAPIRelationshipSchema,
        )

        return relationship_schema

    def create_relationship_data_schema(
        self,
        field_name: str,
        base_name: str,
        field: ModelField,
        relationship_info: RelationshipInfo,
    ) -> Union[Type[BaseJSONAPIRelationshipDataToOneSchema], Type[BaseJSONAPIRelationshipDataToManySchema]]:
        cache_key = (base_name, field_name, relationship_info.resource_type, relationship_info.many)
        if cache_key in self.relationship_schema_cache:
            return self.relationship_schema_cache[cache_key]

        if base_name.endswith("Schema"):
            base_name = base_name[: -len("Schema")]
        schema_name = f"{base_name}{field_name.title()}"
        relationship_schema = self.create_relationship_schema(
            name=schema_name,
            relationship_info=relationship_info,
        )
        base = BaseJSONAPIRelationshipDataToOneSchema
        if relationship_info.many:
            relationship_schema = List[relationship_schema]
            base = BaseJSONAPIRelationshipDataToManySchema

        relationship_data_schema = pydantic.create_model(
            f"{schema_name}RelationshipDataJSONAPI",
            data=(relationship_schema, Field(... if field.required else None)),
            __base__=base,
        )
        self.relationship_schema_cache[cache_key] = relationship_data_schema
        return relationship_data_schema

    def _get_info_from_schema_for_building(
        self,
        base_name: str,
        schema: Type[BaseModel],
        includes: Iterable[str],
    ):
        attributes_schema_fields = {}
        relationships_schema_fields = {}
        included_schemas: List[Tuple[str, BaseModel, str]] = []
        for name, field in (schema.__fields__ or {}).items():
            if isinstance(field.field_info.extra.get("relationship"), RelationshipInfo):
                if includes is not_passed:
                    pass
                elif name not in includes:
                    # if includes are passed, skip this if name not present!
                    continue
                relationship: RelationshipInfo = field.field_info.extra["relationship"]
                relationship_schema = self.create_relationship_data_schema(
                    field_name=name,
                    base_name=base_name,
                    field=field,
                    relationship_info=relationship,
                )
                relationships_schema_fields[name] = (relationship_schema, None)  # allow to not pass relationships
                # works both for to-one and to-many
                included_schemas.append((name, field.type_, relationship.resource_type))
            elif name == "id":
                # skip id field (should be on top)
                continue
            else:
                attributes_schema_fields[name] = (field.outer_type_, field.field_info)

        class ConfigOrmMode(BaseConfig):
            orm_mode = True

        attributes_schema = pydantic.create_model(
            f"{base_name}AttributesJSONAPI",
            **attributes_schema_fields,
            __config__=ConfigOrmMode,
        )

        relationships_schema = pydantic.create_model(
            f"{base_name}RelationshipsJSONAPI",
            **relationships_schema_fields,
            __config__=ConfigOrmMode,
        )

        return attributes_schema, relationships_schema, included_schemas

    def _build_jsonapi_object(
        self,
        base_name: str,
        resource_type: str,
        attributes_schema: Type[TypeSchema],
        relationships_schema: Type[TypeSchema],
        includes,
    ) -> Type[JSONAPIObjectSchema]:
        object_jsonapi_schema_fields = {
            "attributes": (attributes_schema, ...),
        }
        if includes:
            object_jsonapi_schema_fields.update(
                relationships=(relationships_schema, None),  # allow None
            )

        object_jsonapi_schema = pydantic.create_model(
            f"{base_name}ObjectJSONAPI",
            **object_jsonapi_schema_fields,
            type=(str, Field(default=resource_type or self._type, description="Resource type")),
            __base__=JSONAPIObjectSchema,
        )
        return object_jsonapi_schema

    def find_all_included_schemas(
        self,
        schema: Type[BaseModel],
        resource_type: str,
        includes: Iterable[str],
        included_schemas: List[Tuple[str, BaseModel, str]],
    ) -> Dict[str, Type[JSONAPIObjectSchema]]:
        if includes is not_passed:
            return {
                # prepare same object schema
                # TODO: caches?!
                name: self.create_jsonapi_object_schemas(
                    included_schema,
                    resource_type=resource_type,
                ).object_jsonapi_schema
                for (name, included_schema, resource_type) in included_schemas
            }

        can_be_included_schemas = {}
        for i_include in includes:
            current_schema = schema
            relations_list: List[str] = i_include.split(SPLIT_REL)
            for part_index, include_part in enumerate(relations_list, start=1):
                # find nested from the Schema
                nested_schema: Type[BaseModel] = current_schema.__fields__[include_part].type_
                # find all relations for this one
                nested_schema_includes = set(relations_list[: part_index - 1] + relations_list[part_index:])
                related_jsonapi_object_schema = self.create_jsonapi_object_schemas(
                    nested_schema,
                    resource_type=resource_type,
                    # higher and lower
                    includes=nested_schema_includes,
                ).object_jsonapi_schema
                # cache it
                can_be_included_schemas[include_part] = related_jsonapi_object_schema
                # prepare for the next step
                current_schema = nested_schema

        return can_be_included_schemas

    def create_jsonapi_object_schemas(
        self,
        schema: Type[BaseModel],
        includes: Iterable[str] = not_passed,
        resource_type: str = None,
        base_name: str = "",
        compute_included_schemas: bool = False,
    ) -> JSONAPIObjectSchemas:
        if schema in self.object_schemas_cache and includes is not_passed:
            return self.object_schemas_cache[schema]

        schema.update_forward_refs(**registry.schemas)
        base_name = base_name or schema.__name__

        if includes is not not_passed:
            includes = set(includes)

        (
            # pre-built attributed
            attributes_schema,
            # relationships
            relationships_schema,
            # anything that can be included
            included_schemas,
        ) = self._get_info_from_schema_for_building(
            base_name=base_name,
            schema=schema,
            includes=includes,
        )

        object_jsonapi_schema = self._build_jsonapi_object(
            base_name=base_name,
            resource_type=resource_type,
            attributes_schema=attributes_schema,
            relationships_schema=relationships_schema,
            includes=includes,
        )

        can_be_included_schemas = {}
        if compute_included_schemas:
            can_be_included_schemas = self.find_all_included_schemas(
                schema=schema,
                resource_type=resource_type,
                includes=includes,
                included_schemas=included_schemas,
            )

        result = JSONAPIObjectSchemas(
            attributes_schema=attributes_schema,
            relationships_schema=relationships_schema,
            object_jsonapi_schema=object_jsonapi_schema,
            can_be_included_schemas=can_be_included_schemas,
        )
        if includes is not_passed:
            self.object_schemas_cache[schema] = result
        return result

    def build_schema_for_list_result(
        self,
        name: str,
        object_jsonapi_schema: Type[JSONAPIObjectSchema],
        includes_schemas: List[Type[JSONAPIObjectSchema]],
    ) -> Type[JSONAPIResultListSchema]:
        return self.build_schema_for_result(
            name=f"{name}JSONAPI",
            base=JSONAPIResultListSchema,
            data_type=List[object_jsonapi_schema],
            includes_schemas=includes_schemas,
        )

    def build_schema_for_detail_result(
        self,
        name: str,
        object_jsonapi_schema: Type[JSONAPIObjectSchema],
        includes_schemas: List[Type[JSONAPIObjectSchema]],
    ) -> Type[JSONAPIResultDetailSchema]:
        # return detail_jsonapi_schema
        return self.build_schema_for_result(
            name=f"{name}JSONAPI",
            base=JSONAPIResultDetailSchema,
            data_type=object_jsonapi_schema,
            includes_schemas=includes_schemas,
        )

    def build_schema_for_result(
        self,
        name: str,
        base: Type[BaseJSONAPIResultSchema],
        data_type: Union[Type[JSONAPIObjectSchema], Type[List[JSONAPIObjectSchema]]],
        includes_schemas: List[Type[JSONAPIObjectSchema]],
    ) -> Union[Type[JSONAPIResultListSchema], Type[JSONAPIResultDetailSchema]]:
        included_schema_annotation = Union[JSONAPIObjectSchema]
        for includes_schema in includes_schemas:
            included_schema_annotation = Union[included_schema_annotation, includes_schema]

        schema_fields = {
            "data": (data_type, ...),
        }
        if includes_schemas:
            schema_fields.update(
                included=(
                    List[included_schema_annotation],
                    Field(None),
                ),
            )

        result_jsonapi_schema = pydantic.create_model(
            name,
            **schema_fields,
            __base__=base,
        )
        return result_jsonapi_schema
