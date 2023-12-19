"""This module is a CRUD interface between resource managers and the Tortoise ORM"""

from typing import Any, Iterable, Optional, Tuple, Type

from tortoise.queryset import QuerySet

from fastapi_jsonapi.data_layers.base import BaseDataLayer
from fastapi_jsonapi.data_layers.filtering.tortoise_orm import FilterTortoiseORM
from fastapi_jsonapi.data_layers.sorting.tortoise_orm import SortTortoiseORM
from fastapi_jsonapi.data_typing import TypeModel, TypeSchema
from fastapi_jsonapi.querystring import PaginationQueryStringManager, QueryStringManager
from fastapi_jsonapi.schema import BaseJSONAPIItemInSchema


class TortoiseDataLayer(BaseDataLayer):
    """Tortoise data layer"""

    def __init__(
        self,
        schema: Type[TypeSchema],
        model: Type[TypeModel],
        disable_collection_count: bool = False,
        default_collection_count: int = -1,
        id_name_field: Optional[str] = None,
        url_id_field: str = "id",
        query: Optional[QuerySet] = None,
        **kwargs: Any,
    ):
        """
        Initialize an instance of TortoiseDataLayer.

        :param schema:
        :param model: Tortoise
        :param disable_collection_count:
        :param default_collection_count:
        :param id_name_field: Первичный ключ модели
        :param url_id_field: название переменной из FastAPI, в которой придёт значение первичного ключа..
        :param kwargs: initialization parameters of an TortoiseDataLayer instance
        """
        super().__init__(
            schema=schema,
            model=model,
            url_id_field=url_id_field,
            id_name_field=id_name_field,
            disable_collection_count=disable_collection_count,
            default_collection_count=default_collection_count,
            **kwargs,
        )
        self.query_: QuerySet = query or self.model.filter()

    async def create_object(self, data_create: BaseJSONAPIItemInSchema, view_kwargs: dict) -> TypeModel:
        """
        Create an object

        :param data_create: validated data
        :param view_kwargs: kwargs from the resource view
        :return DeclarativeMeta: an object
        """

    async def get_object(self, view_kwargs: dict, qs: Optional[QueryStringManager] = None) -> TypeModel:
        """
        Retrieve an object

        :param view_kwargs: kwargs from the resource view
        :param qs:
        :return DeclarativeMeta: an object
        """

    async def get_collection_count(self, query: QuerySet) -> int:
        """
        Prepare query to fetch collection

        :param query: Tortoise query
        :param qs: QueryString
        :param view_kwargs: view kwargs
        :return:
        """
        if self.disable_collection_count is True:
            return self.default_collection_count

        return await query.count()

    async def get_collection(self, qs: QueryStringManager, view_kwargs: Optional[dict] = None) -> Tuple[int, list]:
        """
        Retrieve a collection of objects through Tortoise.

        :param qs: a querystring manager to retrieve information from url.
        :param view_kwargs: kwargs from the resource view.
        :return: the number of object and the list of objects.
        """
        view_kwargs = view_kwargs or {}
        await self.before_get_collection(qs, view_kwargs)

        query = self.query(view_kwargs)

        if filters_qs := qs.filters:
            filters = FilterTortoiseORM(model=self.model).filter_converter(schema=self.schema, filters=filters_qs)
            for i_filter in filters:
                query = query.filter(**{i_filter[0]: i_filter[1]})

        if sorts := qs.get_sorts(schema=self.schema):
            query = SortTortoiseORM.sort(query=query, query_params_sorting=sorts)

        objects_count = await self.get_collection_count(query)

        query = self.paginate_query(query, qs.pagination)

        collection: Iterable = await query.all()

        collection = await self.after_get_collection(collection, qs, view_kwargs)

        return objects_count, list(collection)

    async def update_object(
        self,
        obj: TypeModel,
        data_update: BaseJSONAPIItemInSchema,
        view_kwargs: dict,
    ) -> bool:
        """
        Update an object through Tortoise.

        :param obj: an object from Tortoise.
        :param data: the data validated by schemas.
        :param view_kwargs: kwargs from the resource view.
        :return: True if object have changed else False.
        """

    async def delete_object(self, obj: TypeModel, view_kwargs: dict):
        """
        Delete an object through Tortoise.

        :param obj: an item from Tortoise.
        :param view_kwargs: kwargs from the resource view.
        """

    async def create_relationship(
        self,
        json_data: dict,
        relationship_field: str,
        related_id_field: str,
        view_kwargs: dict,
    ) -> bool:
        """
        Create a relationship.

        :param json_data: the request params.
        :param relationship_field: the model attribute used for relationship.
        :param related_id_field: the identifier field of the related model.
        :param view_kwargs: kwargs from the resource view.
        :return: True if relationship have changed else False.
        """

    async def get_relationship(
        self,
        relationship_field: str,
        related_type_: str,
        related_id_field: str,
        view_kwargs: dict,
    ) -> Tuple[Any, Any]:
        """
        Get a relationship.

        :param relationship_field: the model attribute used for relationship.
        :param related_type_: the related resource type.
        :param related_id_field: the identifier field of the related model.
        :param view_kwargs: kwargs from the resource view.
        :return: the object and related object(s).
        """

    async def update_relationship(
        self,
        json_data: dict,
        relationship_field: str,
        related_id_field: str,
        view_kwargs: dict,
    ) -> bool:
        """
        Update a relationship

        :param json_data: the request params.
        :param relationship_field: the model attribute used for relationship.
        :param related_id_field: the identifier field of the related model.
        :param view_kwargs: kwargs from the resource view.
        :return: True if relationship have changed else False.
        """

    async def delete_relationship(
        self,
        json_data: dict,
        relationship_field: str,
        related_id_field: str,
        view_kwargs: dict,
    ):
        """
        Delete a relationship.

        :param json_data: the request params.
        :param relationship_field: the model attribute used for relationship.
        :param related_id_field: the identifier field of the related model.
        :param view_kwargs: kwargs from the resource view.
        """

    async def get_related_object(
        self,
        related_model: Type[TypeModel],
        related_id_field: str,
        id_value: str,
    ) -> TypeModel:
        """
        Get related object.

        :param related_model: Tortoise model
        :param related_id_field: the identifier field of the related model
        :param id_value: related object id value
        :return: a related object
        """

    def paginate_query(self, query: QuerySet, paginate_info: PaginationQueryStringManager) -> QuerySet:
        """
        Paginate query according to jsonapi 1.0.

        :param query: Tortoise queryset.
        :param paginate_info: pagination information.
        :return: the paginated query
        """
        if paginate_info.size == 0:
            return query

        query = query.limit(paginate_info.size)
        if paginate_info.number:
            query = query.offset((paginate_info.number - 1) * paginate_info.size)

        return query

    def eagerload_includes(self, query: QuerySet, qs: QueryStringManager) -> QuerySet:
        """
        Use eagerload feature of Tortoise to optimize data retrieval for include querystring parameter.

        :param query: Tortoise queryset.
        :param qs: a querystring manager to retrieve information from url.
        :return: the query with includes eagerloaded.
        """

    def retrieve_object_query(
        self,
        view_kwargs: dict,
        filter_field: Any,
        filter_value: Any,
    ) -> QuerySet:
        """
        Build query to retrieve object.

        :param view_kwargs: kwargs from the resource view
        :param filter_field: the field to filter on
        :param filter_value: the value to filter with
        :return Tortoise query: a query from Tortoise
        """

    def query(self, view_kwargs: dict) -> QuerySet:
        """
        Construct the base query to retrieve wanted data.

        :param view_kwargs: kwargs from the resource view
        """
        return self.query_

    async def before_create_object(self, data: dict, view_kwargs: dict):
        """
        Provide additional data before object creation.

        :param data: the data validated by pydantic.
        :param view_kwargs: kwargs from the resource view.
        """

    async def after_create_object(self, obj: Any, data: dict, view_kwargs: dict):
        """
        Provide additional data after object creation.

        :param obj: an object from data layer.
        :param data: the data validated by pydantic.
        :param view_kwargs: kwargs from the resource view.
        """

    async def before_get_object(self, view_kwargs: dict):
        """
        Make work before to retrieve an object.

        :param view_kwargs: kwargs from the resource view.
        """

    async def after_get_object(self, obj: Any, view_kwargs: dict):
        """
        Make work after to retrieve an object.

        :param obj: an object from data layer.
        :param view_kwargs: kwargs from the resource view.
        """

    async def before_get_collection(self, qs: QueryStringManager, view_kwargs: dict):
        """
        Make work before to retrieve a collection of objects.

        :param qs: a querystring manager to retrieve information from url.
        :param view_kwargs: kwargs from the resource view.
        """

    async def after_get_collection(self, collection: Iterable, qs: QueryStringManager, view_kwargs: dict) -> Iterable:
        """
        Make work after to retrieve a collection of objects.

        :param collection: the collection of objects.
        :param qs: a querystring manager to retrieve information from url.
        :param view_kwargs: kwargs from the resource view.
        """
        return collection

    async def before_update_object(self, obj: Any, data: dict, view_kwargs: dict):
        """
        Make checks or provide additional data before update object.

        :param obj: an object from data layer.
        :param data: the data validated by schemas.
        :param view_kwargs: kwargs from the resource view.
        """

    async def after_update_object(self, obj: Any, data: dict, view_kwargs: dict):
        """
        Make work after update object.

        :param obj: an object from data layer.
        :param data: the data validated by schemas.
        :param view_kwargs: kwargs from the resource view.
        """

    async def before_delete_object(self, obj: Any, view_kwargs: dict):
        """
        Make checks before delete object.

        :param obj: an object from data layer.
        :param view_kwargs: kwargs from the resource view.
        """

    async def after_delete_object(self, obj: Any, view_kwargs: dict):
        """
        Make work after delete object.

        :param obj: an object from data layer.
        :param view_kwargs: kwargs from the resource view.
        """

    async def before_create_relationship(
        self,
        json_data: dict,
        relationship_field: str,
        related_id_field: str,
        view_kwargs: dict,
    ):
        """
        Make work before to create a relationship.

        :param json_data: the request params.
        :param relationship_field: the model attribute used for relationship.
        :param related_id_field: the identifier field of the related model.
        :param view_kwargs: kwargs from the resource view.
        :return boolean: True if relationship have changed else False.
        """

    async def after_create_relationship(
        self,
        obj: Any,
        updated: bool,
        json_data: dict,
        relationship_field: str,
        related_id_field: str,
        view_kwargs: dict,
    ):
        """
        Make work after to create a relationship.

        :param obj: an object from data layer.
        :param updated: True if object was updated else False.
        :param json_data: the request params.
        :param relationship_field: the model attribute used for relationship.
        :param related_id_field: the identifier field of the related model.
        :param view_kwargs: kwargs from the resource view.
        :return boolean: True if relationship have changed else False.
        """

    async def before_get_relationship(
        self,
        relationship_field: str,
        related_type_: str,
        related_id_field: str,
        view_kwargs: dict,
    ):
        """
        Make work before to get information about a relationship.

        :param str relationship_field: the model attribute used for relationship.
        :param str related_type_: the related resource type.
        :param str related_id_field: the identifier field of the related model.
        :param dict view_kwargs: kwargs from the resource view.
        :return tuple: the object and related object(s).
        """

    async def after_get_relationship(
        self,
        obj: Any,
        related_objects: Iterable,
        relationship_field: str,
        related_type_: str,
        related_id_field: str,
        view_kwargs: dict,
    ):
        """
        Make work after to get information about a relationship.

        :param obj: an object from data layer.
        :param related_objects: related objects of the object.
        :param relationship_field: the model attribute used for relationship.
        :param related_type_: the related resource type.
        :param related_id_field: the identifier field of the related model.
        :param view_kwargs: kwargs from the resource view.
        :return tuple: the object and related object(s).
        """

    async def before_update_relationship(
        self,
        json_data: dict,
        relationship_field: str,
        related_id_field: str,
        view_kwargs: dict,
    ):
        """
        Make work before to update a relationship.

        :param json_data: the request params.
        :param relationship_field: the model attribute used for relationship.
        :param related_id_field: the identifier field of the related model.
        :param view_kwargs: kwargs from the resource view.
        :return boolean: True if relationship have changed else False.
        """

    async def after_update_relationship(
        self,
        obj: Any,
        updated: bool,
        json_data: dict,
        relationship_field: str,
        related_id_field: str,
        view_kwargs: dict,
    ):
        """
        Make work after to update a relationship.

        :param obj: an object from data layer.
        :param updated: True if object was updated else False.
        :param json_data: the request params.
        :param relationship_field: the model attribute used for relationship.
        :param related_id_field: the identifier field of the related model.
        :param view_kwargs: kwargs from the resource view.
        :return boolean: True if relationship have changed else False.
        """

    async def before_delete_relationship(
        self,
        json_data: dict,
        relationship_field: str,
        related_id_field: str,
        view_kwargs: dict,
    ):
        """
        Make work before to delete a relationship.

        :param json_data: the request params.
        :param relationship_field: the model attribute used for relationship.
        :param related_id_field: the identifier field of the related model.
        :param view_kwargs: kwargs from the resource view.
        """

    async def after_delete_relationship(
        self,
        obj: Any,
        updated: bool,
        json_data: dict,
        relationship_field: str,
        related_id_field: str,
        view_kwargs: dict,
    ):
        """
        Make work after to delete a relationship.

        :param obj: an object from data layer.
        :param updated: True if object was updated else False.
        :param json_data: the request params.
        :param relationship_field: the model attribute used for relationship.
        :param related_id_field: the identifier field of the related model.
        :param view_kwargs: kwargs from the resource view.
        """
