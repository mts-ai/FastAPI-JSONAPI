import inspect
import logging
from functools import partial
from typing import Any, Callable, ClassVar, Iterable, Optional, Type

from fastapi import Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel as PydanticBaseModel

from fastapi_jsonapi.common import get_relationship_info_from_field_metadata
from fastapi_jsonapi.data_layers.base import BaseDataLayer
from fastapi_jsonapi.data_typing import TypeModel, TypeSchema
from fastapi_jsonapi.exceptions import BadRequest
from fastapi_jsonapi.querystring import QueryStringManager
from fastapi_jsonapi.schema import BaseJSONAPIItemInSchema
from fastapi_jsonapi.schema_base import BaseModel
from fastapi_jsonapi.storages.models_storage import models_storage
from fastapi_jsonapi.storages.schemas_storage import schemas_storage
from fastapi_jsonapi.types_metadata import RelationshipInfo
from fastapi_jsonapi.views import Operation, OperationConfig, RelationshipRequestInfo

logger = logging.getLogger(__name__)


class ViewBase:
    """
    Views are inited for each request
    """

    data_layer_cls = BaseDataLayer
    operation_dependencies: ClassVar[dict[Operation, OperationConfig]] = {}

    def __init__(
        self,
        *,
        request: Request,
        resource_type: str,
        operation: Operation,
        model: Type[TypeModel],
        schema: Type[TypeSchema],
        **options,
    ):
        self.request: Request = request
        self.query_params: QueryStringManager
        self.resource_type: str = resource_type
        self.operation: Operation = operation
        self.model: Type[TypeModel] = model
        self.schema: Type[TypeSchema] = schema
        self.options: dict = options
        self.query_params: QueryStringManager = QueryStringManager(request=request)

    async def get_data_layer(
        self,
        extra_view_deps: dict[str, Any],
    ) -> BaseDataLayer:
        """
        Prepares data layer for detail view

        :param extra_view_deps:
        :return:
        """
        dl_kwargs = await self.handle_endpoint_dependencies(extra_view_deps)
        return self.data_layer_cls(
            request=self.request,
            model=self.model,
            schema=self.schema,
            resource_type=self.resource_type,
            **dl_kwargs,
        )

    async def handle_get_resource_detail(
        self,
        obj_id: str,
        **extra_view_deps,
    ) -> dict:
        dl: BaseDataLayer = await self.get_data_layer(extra_view_deps)

        view_kwargs = {dl.url_id_field: obj_id}
        db_object = await dl.get_object(view_kwargs=view_kwargs, qs=self.query_params)

        return self._build_detail_response(db_object)

    async def handle_get_resource_relationship(
        self,
        obj_id: str,
        relationship_name: str,
        parent_resource_type: str,
        **extra_view_deps,
    ) -> dict:
        dl: BaseDataLayer = await self.get_data_layer(extra_view_deps)
        view_kwargs = {dl.url_id_field: obj_id}
        db_object = await dl.get_object(
            view_kwargs=view_kwargs,
            qs=self.query_params,
            relationship_request_info=RelationshipRequestInfo(
                parent_resource_type=parent_resource_type,
                parent_obj_id=obj_id,
                relationship_name=relationship_name,
            ),
        )
        return self._build_detail_response(db_object)

    async def handle_get_resource_relationship_list(
        self,
        obj_id: str,
        relationship_name: str,
        parent_resource_type: str,
        **extra_view_deps,
    ) -> dict:
        dl: BaseDataLayer = await self.get_data_layer(extra_view_deps)
        count, items_from_db = await dl.get_collection(
            qs=self.query_params,
            relationship_request_info=RelationshipRequestInfo(
                parent_resource_type=parent_resource_type,
                parent_obj_id=obj_id,
                relationship_name=relationship_name,
            ),
        )
        total_pages = self._calculate_total_pages(count)
        return self._build_list_response(items_from_db, count, total_pages)

    async def handle_update_resource(
        self,
        obj_id: str,
        data_update: BaseJSONAPIItemInSchema,
        **extra_view_deps,
    ) -> dict:
        dl: BaseDataLayer = await self.get_data_layer(extra_view_deps)
        return await self.process_update_object(dl=dl, obj_id=obj_id, data_update=data_update)

    async def process_update_object(
        self,
        dl: BaseDataLayer,
        obj_id: str,
        data_update: BaseJSONAPIItemInSchema,
    ) -> dict:
        if obj_id != data_update.id:
            raise BadRequest(
                detail="obj_id and data.id should be same.",
                pointer="/data/id",
            )
        view_kwargs = {
            dl.url_id_field: obj_id,
            "required_to_load": data_update.attributes.model_fields.keys(),
        }
        db_object = await dl.get_object(view_kwargs=view_kwargs, qs=self.query_params)

        await dl.update_object(db_object, data_update, view_kwargs)

        return self._build_detail_response(db_object)

    async def handle_delete_resource(
        self,
        obj_id: str,
        **extra_view_deps,
    ) -> None:
        dl: BaseDataLayer = await self.get_data_layer(extra_view_deps)
        await self.process_delete_object(dl=dl, obj_id=obj_id)

    async def process_delete_object(
        self,
        dl: BaseDataLayer,
        obj_id: str,
    ) -> None:
        view_kwargs = {dl.url_id_field: obj_id}
        db_object = await dl.get_object(view_kwargs=view_kwargs, qs=self.query_params)

        await dl.delete_object(db_object, view_kwargs)

    async def handle_get_resource_list(self, **extra_view_deps) -> dict:
        dl: BaseDataLayer = await self.get_data_layer(extra_view_deps)
        count, items_from_db = await dl.get_collection(qs=self.query_params)
        total_pages = self._calculate_total_pages(count)

        return self._build_list_response(items_from_db, count, total_pages)

    async def handle_post_resource_list(
        self,
        data_create: BaseJSONAPIItemInSchema,
        **extra_view_deps,
    ) -> dict:
        dl: BaseDataLayer = await self.get_data_layer(extra_view_deps)
        return await self.process_create_object(dl=dl, data_create=data_create)

    async def process_create_object(self, dl: BaseDataLayer, data_create: BaseJSONAPIItemInSchema) -> dict:
        db_object = await dl.create_object(data_create=data_create, view_kwargs={})

        view_kwargs = {dl.url_id_field: models_storage.get_object_id(db_object, self.resource_type)}
        if self.query_params.include:
            db_object = await dl.get_object(view_kwargs=view_kwargs, qs=self.query_params)

        return self._build_detail_response(db_object)

    async def handle_delete_resource_list(self, **extra_view_deps) -> dict:
        dl: BaseDataLayer = await self.get_data_layer(extra_view_deps)
        count, items_from_db = await dl.get_collection(qs=self.query_params)
        total_pages = self._calculate_total_pages(count)

        await dl.delete_objects(items_from_db, {})

        return self._build_list_response(items_from_db, count, total_pages)

    async def _run_handler(
        self,
        handler: Callable,
        dto: Optional[BaseModel] = None,
    ):
        handler = partial(handler, self, dto) if dto is not None else partial(handler, self)

        if inspect.iscoroutinefunction(handler):
            return await handler()

        return await run_in_threadpool(handler)

    async def _handle_config(
        self,
        config: OperationConfig,
        extra_view_deps: dict[str, Any],
    ) -> dict[str, Any]:
        if config.handler is None:
            return {}

        if config.dependencies:
            dto_class: Type[PydanticBaseModel] = config.dependencies
            dto = dto_class(**extra_view_deps)
            return await self._run_handler(config.handler, dto)

        return await self._run_handler(config.handler)

    async def handle_endpoint_dependencies(
        self,
        extra_view_deps: dict[str, Any],
    ) -> dict:
        """
        :return dict: this is **kwargs for DataLayer.__init___
        """
        dl_kwargs = {}
        if common_method_config := self.operation_dependencies.get(Operation.ALL):
            dl_kwargs.update(await self._handle_config(common_method_config, extra_view_deps))

        if method_config := self.operation_dependencies.get(self.operation):
            dl_kwargs.update(await self._handle_config(method_config, extra_view_deps))

        return dl_kwargs

    def _calculate_total_pages(self, db_items_count: int) -> int:
        total_pages = 1
        if not (pagination_size := self.query_params.pagination.size):
            return total_pages

        return db_items_count // pagination_size + (
            # one more page if not a multiple of size
            (db_items_count % pagination_size)
            and 1
        )

    @classmethod
    def _prepare_item_data(
        cls,
        db_item,
        resource_type: str,
        include_fields: Optional[dict[str, dict[str, Type[TypeSchema]]]] = None,
    ) -> dict:
        attrs_schema = schemas_storage.get_attrs_schema(resource_type, operation_type="get")

        if include_fields is None or not (field_schemas := include_fields.get(resource_type)):
            id_val = models_storage.get_object_id(
                db_object=db_item,
                resource_type=resource_type,
            )
            data_schema = schemas_storage.get_data_schema(resource_type, operation_type="get")
            return data_schema(
                id=f"{id_val}",
                attributes=attrs_schema.model_validate(db_item),
            ).model_dump()

        result_attributes = {}
        # empty str means skip all attributes
        if "" not in field_schemas:
            pre_values = {}
            for field_name, field_schema in field_schemas.items():
                pre_values[field_name] = getattr(db_item, field_name)

            before_validators, after_validators = schemas_storage.get_model_validators(
                resource_type,
                operation_type="get",
            )
            if before_validators:
                for validator_name, validator in before_validators.items():
                    if hasattr(validator.wrapped, "__func__"):
                        pre_values = validator.wrapped.__func__(attrs_schema, pre_values)
                        continue

                    pre_values = validator.wrapped(pre_values)

            for field_name, field_schema in field_schemas.items():
                validated_model = field_schema(**{field_name: pre_values[field_name]})

                if after_validators:
                    for validator_name, validator in after_validators.items():
                        if hasattr(validator.wrapped, "__func__"):
                            validated_model = validator.wrapped.__func__(attrs_schema, validated_model)
                            continue

                        validated_model = validator.wrapped(validated_model)

                result_attributes[field_name] = getattr(validated_model, field_name)

        return {
            "id": f"{models_storage.get_object_id(db_item, resource_type)}",
            "type": resource_type,
            "attributes": result_attributes,
        }

    def _prepare_include_params(self) -> list[list[str]]:
        result = []
        includes = sorted(self.query_params.include)
        prev, *_ = includes

        for include in includes:
            if not include.startswith(prev):
                result.append(prev.split("."))

            prev = include

        result.append(prev.split("."))
        return result

    @classmethod
    def _get_include_key(cls, db_item: TypeModel, info: RelationshipInfo) -> tuple[str, str]:
        return info.resource_type, str(getattr(db_item, info.id_field_name))

    def _process_includes(
        self,
        db_items: list[TypeModel],
        items_data: list[dict],
        resource_type: str,
        include_paths: list[Iterable[str]],
        include_fields: dict[str, dict[str, Type[TypeSchema]]],
        result_included: Optional[dict] = None,
    ) -> dict[tuple[str, str], dict]:
        result_included = result_included or {}

        for db_item, item_data in zip(db_items, items_data):
            item_data["relationships"] = item_data.get("relationships", {})

            for path in include_paths:
                target_relationship, *include_path = path
                info: RelationshipInfo = schemas_storage.get_relationship_info(
                    resource_type=resource_type,
                    operation_type="get",
                    field_name=target_relationship,
                )
                db_items_to_process: list[TypeModel] = []
                items_data_to_process: list[dict] = []

                if info.many:
                    relationship_data = []

                    for relationship_db_item in getattr(db_item, target_relationship):
                        include_key = self._get_include_key(relationship_db_item, info)

                        if not (relationship_item_data := result_included.get(include_key)):
                            relationship_item_data = self._prepare_item_data(
                                db_item=relationship_db_item,
                                resource_type=info.resource_type,
                                include_fields=include_fields,
                            )
                            result_included[include_key] = relationship_item_data

                        db_items_to_process.append(relationship_db_item)
                        relationship_data.append(
                            {
                                "id": str(getattr(relationship_db_item, info.id_field_name)),
                                "type": info.resource_type,
                            },
                        )
                        items_data_to_process.append(relationship_item_data)
                else:
                    if (relationship_db_item := getattr(db_item, target_relationship)) is None:
                        item_data["relationships"][target_relationship] = {"data": None}
                        continue

                    db_items_to_process.append(relationship_db_item)
                    relationship_data = {
                        "id": str(getattr(relationship_db_item, info.id_field_name)),
                        "type": info.resource_type,
                    }

                    include_key = self._get_include_key(relationship_db_item, info)

                    if not (relationship_item_data := result_included.get(include_key)):
                        relationship_item_data = self._prepare_item_data(relationship_db_item, info.resource_type)
                        result_included[include_key] = relationship_item_data

                    items_data_to_process.append(relationship_item_data)

                if include_path:
                    self._process_includes(
                        db_items=db_items_to_process,
                        items_data=items_data_to_process,
                        resource_type=info.resource_type,
                        include_paths=[include_path],
                        result_included=result_included,
                        include_fields=include_fields,
                    )

                item_data["relationships"][target_relationship] = {"data": relationship_data}

        return result_included

    @classmethod
    def _get_schema_field_names(cls, schema: type[TypeSchema]) -> set[str]:
        """Returns all attribute names except relationships"""
        result = set()

        for field_name, field in schema.model_fields.items():
            if get_relationship_info_from_field_metadata(field):
                continue

            result.add(field_name)

        return result

    def _get_include_fields(self) -> dict[str, dict[str, Type[TypeSchema]]]:
        include_fields = {}
        for resource_type, field_names in self.query_params.fields.items():
            include_fields[resource_type] = {}

            for field_name in field_names:
                include_fields[resource_type][field_name] = schemas_storage.get_field_schema(
                    resource_type=resource_type,
                    operation_type="get",
                    field_name=field_name,
                )

        return include_fields

    def _build_detail_response(self, db_item: TypeModel) -> dict:
        include_fields = self._get_include_fields()
        item_data = self._prepare_item_data(db_item, self.resource_type, include_fields)
        response = {
            "data": item_data,
            "jsonapi": {"version": "1.0"},
            "meta": None,
        }

        if self.query_params.include:
            included = self._process_includes(
                db_items=[db_item],
                items_data=[item_data],
                include_paths=self._prepare_include_params(),
                resource_type=self.resource_type,
                include_fields=include_fields,
            )
            response["included"] = [value for _, value in sorted(included.items(), key=lambda item: item[0])]

        return response

    def _build_list_response(
        self,
        items_from_db: list[TypeModel],
        count: int,
        total_pages: int,
    ) -> dict:
        include_fields = self._get_include_fields()
        items_data = [
            self._prepare_item_data(db_item, self.resource_type, include_fields) for db_item in items_from_db
        ]
        response = {
            "data": items_data,
            "jsonapi": {"version": "1.0"},
            "meta": {"count": count, "totalPages": total_pages},
        }

        if self.query_params.include:
            included = self._process_includes(
                db_items=items_from_db,
                items_data=items_data,
                resource_type=self.resource_type,
                include_paths=self._prepare_include_params(),
                include_fields=include_fields,
            )
            response["included"] = [value for _, value in sorted(included.items(), key=lambda item: item[0])]

        return response
