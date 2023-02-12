"""JSON API router class."""
from dataclasses import dataclass
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Type,
    Union,
    TypeVar,
    Tuple,
    Iterable,
    Callable,
)

import pydantic
from pydantic import BaseConfig
from pydantic.fields import ModelField
from fastapi import APIRouter
from fastapi_rest_jsonapi.schema_base import BaseModel, Field, registry, RelationshipInfo

from fastapi_rest_jsonapi.data_layers.data_typing import TypeModel
from fastapi_rest_jsonapi.data_layers.orm import DBORMType
from fastapi_rest_jsonapi.exceptions import ExceptionResponseSchema
from fastapi_rest_jsonapi.methods import (
    delete_detail_jsonapi,
    get_detail_jsonapi,
    get_list_jsonapi,
    patch_detail_jsonapi,
    post_list_jsonapi,
    delete_list_jsonapi,
)
from fastapi_rest_jsonapi.schema import (
    BasePatchJSONAPISchema,
    BasePostJSONAPISchema,
    JSONAPIObjectSchema,
    JSONAPIResultDetailSchema,
    JSONAPIResultListSchema,
    BaseJSONAPIRelationshipSchema,
    BaseJSONAPIRelationshipDataToOneSchema,
    BaseJSONAPIRelationshipDataToManySchema,
    BaseJSONAPIItemSchema,
    BaseJSONAPIResultSchema,
)
from fastapi_rest_jsonapi.schema_base import registry

JSON_API_RESPONSE_TYPE = Optional[Dict[Union[int, str], Dict[str, Any]]]


not_passed = object()


@dataclass(frozen=True, slots=True)
class JSONAPIObjectSchemas:
    attributes_schema: Type[BaseModel]
    relationships_schema: Type[BaseModel]
    object_jsonapi_schema: Type[JSONAPIObjectSchema]
    can_be_included_schemas: Dict[str, Type[JSONAPIObjectSchema]]


class RoutersJSONAPI:
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
        model: Type[TypeModel],
        engine: DBORMType = DBORMType.sqlalchemy,
        schema_detail: Type[BaseModel] = None,
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
        :params schema: schemas схема ресурса (полная)
        :params type_resource: тип ресурса, будет отображаться при выгрузке, необходимый параметр JSON:API.
        :params schema_in_patch: schemas схема с полями, которые можно изменять.
        :params schema_in_post: schemas схема с полями, которые нужно отправлять для создания новой сущности.
        :params model: Модель данных, например модель данных от SQLAlchemy или Tortoise ORM.
        :params engine: тип движка, какой тип моделей нужно использовать, например SQLAlchemy или Tortoise ORM.
                        Необходимо для автоматического построения запросов.
        :params schema_detail: Схема для detail resource. Если не передано, будет использовано значение schema.
        """
        self._routers: APIRouter = routers
        self._path: Union[str, List[str]] = path
        self._tags: List[str] = tags
        self.class_detail: Any = class_detail
        self.detail_views: Any = class_detail(jsonapi=self)
        self.class_list: Any = class_list
        self.list_views: Any = class_list(jsonapi=self)
        self._type: str = type_resource
        self._schema: Type[BaseModel] = schema
        self.schema_list: Type[BaseModel] = schema
        self.model: Type[TypeModel] = model
        self._engine: DBORMType = engine
        self.schema_detail = schema_detail or schema

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
        # post_create_schema = self.get_schema_for_create(
        #     name=schema_in_post.__name__,
        #     can_be_included,
        # )
        self._schema_in_post_base: Type[BaseModel] = schema_in_post
        self._schema_in_post: Type[BaseModel] = post_jsonapi_schema

        object_jsonapi_detail_schema, detail_jsonapi_schema = self.build_detail_schemas(self.schema_detail)
        self.object_jsonapi_detail_schema: Type[JSONAPIObjectSchema] = object_jsonapi_detail_schema
        self.detail_response_schema: Type[JSONAPIResultDetailSchema] = detail_jsonapi_schema

        object_jsonapi_list_schema, list_jsonapi_schema = self.build_list_schemas(self.schema_list)
        self.object_jsonapi_list_schema: Type[JSONAPIObjectSchema] = object_jsonapi_list_schema
        self.list_response_schema: Type[JSONAPIResultListSchema] = list_jsonapi_schema

        if isinstance(self._path, Iterable) and not isinstance(self._path, (str, bytes)):
            for i_path in self._path:
                self._add_routers(i_path)
        else:
            self._add_routers(self._path)

    def _build_schema(
        self,
        base_name: str,
        schema: Type[BaseModel],
        builder: Callable[
            [...],
            Tuple[Type[JSONAPIObjectSchema], Union[Type[JSONAPIResultDetailSchema], Type[JSONAPIResultListSchema]]],
        ],
    ):
        object_schemas = self.create_jsonapi_object_schemas(
            schema=schema,
            base_name=base_name,
            compute_included_schemas=True,
        )
        object_jsonapi_schema = object_schemas.object_jsonapi_schema
        can_be_included = list(object_schemas.can_be_included_schemas.values())
        list_jsonapi_schema = builder(
            name=base_name,
            object_jsonapi_schema=object_jsonapi_schema,
            includes_schemas=can_be_included,
        )
        return object_jsonapi_schema, list_jsonapi_schema

    def build_detail_schemas(
        self,
        schema: Type[BaseModel],
    ) -> Tuple[Type[JSONAPIObjectSchema], Type[JSONAPIResultDetailSchema]]:
        return self._build_schema(
            base_name=f"{schema.__name__}Detail",
            schema=schema,
            builder=self.build_schema_for_detail_result,
        )

    def build_list_schemas(
        self,
        schema: Type[BaseModel],
    ) -> Tuple[Type[JSONAPIObjectSchema], Type[JSONAPIResultListSchema]]:
        return self._build_schema(
            base_name=f"{schema.__name__}List",
            schema=schema,
            builder=self.build_schema_for_list_result,
        )

    def _add_routers(self, path: str):
        """Add new router."""
        error_responses: Optional[JSON_API_RESPONSE_TYPE] = {
            400: {"model": ExceptionResponseSchema},
            401: {"model": ExceptionResponseSchema},
            404: {"model": ExceptionResponseSchema},
            500: {"model": ExceptionResponseSchema},
        }
        if hasattr(self.list_views, "get"):
            # Добавляем в APIRouter API с выгрузкой списка элементов данного ресурса
            self._routers.get(
                path,
                tags=self._tags,
                response_model=self.list_response_schema,
                response_model_exclude_unset=True,
                responses=error_responses,
                summary=f"Get list of `{self._type}` objects",
            )(
                # Оборачиваем декоратором, который создаст сигнатуру функции для FastAPI
                get_list_jsonapi(
                    schema=self._schema,
                    type_=self._type,
                    schema_resp=self.list_response_schema,
                    model=self.model,
                    engine=self._engine,
                )(self.list_views.get)
            )

        if hasattr(self.list_views, "post"):
            self._routers.post(
                path,
                tags=self._tags,
                response_model=self.detail_response_schema,
                response_model_exclude_unset=True,
                responses=error_responses,
                summary=f"Create object `{self._type}`",
            )(
                post_list_jsonapi(
                    schema=self._schema,
                    schema_in=self._schema_in_post,
                    type_=self._type,
                    schema_resp=self.detail_response_schema,
                    model=self.model,
                    engine=self._engine,
                )(self.list_views.post)
            )

        if hasattr(self.list_views, "delete"):
            self._routers.delete(path, tags=self._tags, summary=f"Delete list objects of type `{self._type}`")(
                delete_list_jsonapi(
                    schema=self._schema,
                    model=self.model,
                    engine=self._engine,
                )(self.list_views.delete)
            )

        if hasattr(self.detail_views, "get"):
            self._routers.get(
                path + "/{obj_id}",
                tags=self._tags,
                response_model=self.detail_response_schema,
                response_model_exclude_unset=True,
                responses=error_responses,
                summary=f"Get object `{self._type}` by id",
            )(
                get_detail_jsonapi(
                    schema=self._schema,
                    schema_resp=self.detail_response_schema,
                    model=self.model,
                    engine=self._engine,
                )(self.detail_views.get)
            )

        if hasattr(self.detail_views, "patch"):
            self._routers.patch(
                path + "/{obj_id}",
                tags=self._tags,
                response_model=self.detail_response_schema,
                response_model_exclude_unset=True,
                responses=error_responses,
                summary=f"Update object `{self._type}` by id",
            )(
                patch_detail_jsonapi(
                    schema=self._schema,
                    schema_in=self._schema_in_patch,
                    type_=self._type,
                    schema_resp=self.detail_response_schema,
                    model=self.model,
                    engine=self._engine,
                )(self.detail_views.patch)
            )

        if hasattr(self.detail_views, "delete"):
            self._routers.delete(path + "/{obj_id}", tags=self._tags, summary=f"Delete object of type `{self._type}`")(
                delete_detail_jsonapi(
                    schema=self._schema,
                    model=self.model,
                    engine=self._engine,
                )(self.detail_views.delete)
            )

    def create_relationship_schema(
        self,
        name: str,
        relationship_info: RelationshipInfo,
    ) -> Type[BaseJSONAPIRelationshipSchema]:
        if name.endswith("s"):
            # plural to single
            name = name[:-1]

        relationship_schema = pydantic.create_model(
            f"{name}RelationshipJSONAPI".format(name=name),
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
    ) -> Tuple[Type[BaseJSONAPIRelationshipDataToOneSchema], Type[BaseJSONAPIRelationshipDataToManySchema]]:
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
        return relationship_data_schema

    def create_jsonapi_object_schemas(
        self,
        schema: Type[BaseModel],
        includes: Iterable[str] = not_passed,
        resource_type: str = None,
        base_name: str = "",
        compute_included_schemas: bool = False,
    ) -> JSONAPIObjectSchemas:
        schema.update_forward_refs(**registry.schemas)
        base_name = base_name or schema.__name__

        if includes is not not_passed:
            includes = set(includes)

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
                relationships_schema_fields[name] = (relationship_schema, None)  # allow to not pass relationshps
                # works both for to-one and to-many
                included_schemas.append((name, field.type_, relationship.resource_type))
            elif name == "id":
                # skip id field (should be on top)
                continue
            else:
                attributes_schema_fields[name] = (field.type_, field.field_info)

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

        object_jsonapi_schema_fields = dict(
            attributes=(attributes_schema, ...),
        )
        if includes:
            # we don't need `"relationships": null` in responses w/o relationships
            object_jsonapi_schema_fields.update(
                relationships=(relationships_schema, None),  # allow None
            )

        object_jsonapi_schema = pydantic.create_model(
            f"{base_name}ObjectJSONAPI",
            **object_jsonapi_schema_fields,
            type=(str, Field(default=resource_type or self._type, description="Resource type")),
            __base__=JSONAPIObjectSchema,
        )
        can_be_included_schemas = {}
        if compute_included_schemas:
            can_be_included_schemas = {
                # prepare same object schema
                # TODO: caches?!
                name: self.create_jsonapi_object_schemas(
                    included_schema,
                    resource_type=resource_type,
                ).object_jsonapi_schema
                for (name, included_schema, resource_type) in included_schemas
            }
        return JSONAPIObjectSchemas(
            attributes_schema=attributes_schema,
            relationships_schema=relationships_schema,
            object_jsonapi_schema=object_jsonapi_schema,
            can_be_included_schemas=can_be_included_schemas,
        )

    @classmethod
    def build_schema_for_list_result(
        cls,
        name: str,
        object_jsonapi_schema: Type[JSONAPIObjectSchema],
        includes_schemas: List[Type[JSONAPIObjectSchema]],
    ) -> Type[JSONAPIResultListSchema]:
        return cls.build_schema_for_result(
            name=f"{name}JSONAPI",
            base=JSONAPIResultListSchema,
            data_type=List[object_jsonapi_schema],
            includes_schemas=includes_schemas,
        )

    @classmethod
    def build_schema_for_detail_result(
        cls,
        name: str,
        object_jsonapi_schema: Type[JSONAPIObjectSchema],
        includes_schemas: List[Type[JSONAPIObjectSchema]],
    ) -> Type[JSONAPIResultDetailSchema]:
        # return detail_jsonapi_schema
        return cls.build_schema_for_result(
            name=f"{name}JSONAPI",
            base=JSONAPIResultDetailSchema,
            data_type=object_jsonapi_schema,
            includes_schemas=includes_schemas,
        )

    @classmethod
    def build_schema_for_result(
        cls,
        name: str,
        base: Type[BaseJSONAPIResultSchema],
        data_type: Union[Type[JSONAPIObjectSchema], Type[List[JSONAPIObjectSchema]]],
        includes_schemas: List[Type[JSONAPIObjectSchema]],
    ) -> Union[Type[JSONAPIResultListSchema], Type[JSONAPIResultDetailSchema]]:
        schema_fields = dict(
            data=(data_type, ...),
            included=(List[JSONAPIObjectSchema], None),
        )
        # TODO!
        # if includes_schemas:
        #     schema_fields.update(included=(List[Union[includes_schemas[0]]], None))
        result_jsonapi_schema = pydantic.create_model(
            name,
            **schema_fields,
            __base__=base,
        )
        return result_jsonapi_schema
