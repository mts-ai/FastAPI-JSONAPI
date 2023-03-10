"""This module is a CRUD interface between resource managers and the sqlalchemy ORM"""
from typing import Any, Iterable, Type, Optional, Tuple

from tortoise.queryset import QuerySet

from fastapi_jsonapi.querystring import QueryStringManager, PaginationQueryStringManager
from fastapi_jsonapi.data_layers.base import BaseDataLayer
from fastapi_jsonapi.data_layers.data_typing import TypeSchema, TypeModel
from fastapi_jsonapi.data_layers.filtering.tortoise_orm import FilterTortoiseORM
from fastapi_jsonapi.data_layers.sorting.tortoise_orm import SortTortoiseORM


class TortoiseORMEngine(BaseDataLayer):
    """Sqlalchemy data layer"""

    def __init__(
        self,
        schema: Type[TypeSchema],
        model: Type[TypeModel],
        disable_collection_count: bool = False,
        default_collection_count: int = -1,
        id_name_field: Optional[str] = None,
        url_field: str = "id",
        query: Optional[QuerySet] = None,
        **kwargs: Any,
    ):
        """
        Initialize an instance of SqlalchemyDataLayer.

        :params schema:
        :params model: Tortoise
        :params disable_collection_count: Resource's attribute `disable_collection_count`
                                          has to be bool or list/tuple with exactly 2 values!\n
        :params default_collection_count: For example `disable_collection_count = (True, 999)`
        :params id_name_field: Первичный ключ модели
        :params url_field: название переменной из FastAPI, в которой придёт значение первичного ключа..
        :params kwargs: initialization parameters of an SqlalchemyDataLayer instance
        """
        super().__init__(kwargs)

        self.disable_collection_count: bool = disable_collection_count
        self.default_collection_count: int = default_collection_count
        self.schema = schema
        self.model = model
        self.query_: QuerySet = query or model.filter()
        self.id_name_field = id_name_field
        self.url_field = url_field

    async def create_object(self, data: dict, view_kwargs: dict):
        """
        Create an object through sqlalchemy.

        :params data: the data validated by marshmallow.
        :params view_kwargs: kwargs from the resource view.
        :return DeclarativeMeta: an object from sqlalchemy.
        """
        pass

    async def get_object(self, view_kwargs: dict, qs: Optional[QueryStringManager] = None) -> TypeModel:
        """
        Retrieve an object through sqlalchemy.

        :params view_kwargs: kwargs from the resource view
        :params qs:
        :return DeclarativeMeta: an object from sqlalchemy
        """
        pass

    async def get_collection_count(self, query: QuerySet) -> int:
        """
        :params query: SQLAlchemy query
        :params qs: QueryString
        :params view_kwargs: view kwargs
        :return:
        """
        if self.disable_collection_count is True:
            return self.default_collection_count

        return await query.count()

    async def get_collection(self, qs: QueryStringManager, view_kwargs: Optional[dict] = None) -> Tuple[int, Iterable]:
        """
        Retrieve a collection of objects through sqlalchemy.

        :params qs: a querystring manager to retrieve information from url.
        :params view_kwargs: kwargs from the resource view.
        :return: the number of object and the list of objects.
        """
        view_kwargs = view_kwargs or {}
        await self.before_get_collection(qs, view_kwargs)

        query = self.query(view_kwargs)

        if qs.filters:
            filters = FilterTortoiseORM(model=self.model).filter_converter(schema=self.schema, filters=qs.filters)
            for i_filter in filters:
                query = query.filter(**{i_filter[0]: i_filter[1]})

        if qs.sorting:
            query = SortTortoiseORM.sort(query=query, query_params_sorting=qs.sorting)

        objects_count = await self.get_collection_count(query)

        query = self.paginate_query(query, qs.pagination)

        collection: Iterable = await query.all()

        collection = await self.after_get_collection(collection, qs, view_kwargs)

        return objects_count, collection

    async def update_object(self, obj: Any, data: dict, view_kwargs: dict) -> bool:
        """
        Update an object through sqlalchemy.

        :params obj: an object from sqlalchemy.
        :params data: the data validated by pydantic.
        :params view_kwargs: kwargs from the resource view.
        :return: True if object have changed else False.
        """
        pass

    async def delete_object(self, obj: Any, view_kwargs: dict):
        """
        Delete an object through sqlalchemy.

        :params obj: an item from sqlalchemy.
        :params view_kwargs: kwargs from the resource view.
        """
        pass

    async def create_relationship(
        self,
        json_data: dict,
        relationship_field: str,
        related_id_field: str,
        view_kwargs: dict,
    ) -> bool:
        """
        Create a relationship.

        :params json_data: the request params.
        :params relationship_field: the model attribute used for relationship.
        :params related_id_field: the identifier field of the related model.
        :params view_kwargs: kwargs from the resource view.
        :return: True if relationship have changed else False.
        """
        pass

    async def get_relationship(
        self,
        relationship_field: str,
        related_type_: str,
        related_id_field: str,
        view_kwargs: dict,
    ) -> Tuple[Any, Any]:
        """
        Get a relationship.

        :params relationship_field: the model attribute used for relationship.
        :params related_type_: the related resource type.
        :params related_id_field: the identifier field of the related model.
        :params view_kwargs: kwargs from the resource view.
        :return: the object and related object(s).
        """
        pass

    async def update_relationship(
        self,
        json_data: dict,
        relationship_field: str,
        related_id_field: str,
        view_kwargs: dict,
    ) -> bool:
        """
        Update a relationship

        :params json_data: the request params.
        :params relationship_field: the model attribute used for relationship.
        :params related_id_field: the identifier field of the related model.
        :param view_kwargs: kwargs from the resource view.
        :return: True if relationship have changed else False.
        """
        pass

    async def delete_relationship(
        self,
        json_data: dict,
        relationship_field: str,
        related_id_field: str,
        view_kwargs: dict,
    ):
        """
        Delete a relationship.

        :params json_data: the request params.
        :params relationship_field: the model attribute used for relationship.
        :params related_id_field: the identifier field of the related model.
        :params view_kwargs: kwargs from the resource view.
        """
        pass

    async def get_related_object(self, related_model: TypeModel, related_id_field: str, obj: Any) -> Any:
        """
        Get a related object.

        :params related_model: an sqlalchemy model
        :params related_id_field: the identifier field of the related model
        :params obj: the sqlalchemy object to retrieve related objects from
        :return: a related object
        """
        pass

    def paginate_query(self, query: QuerySet, paginate_info: PaginationQueryStringManager) -> QuerySet:
        """
        Paginate query according to jsonapi 1.0.

        :params query: sqlalchemy queryset.
        :params paginate_info: pagination information.
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
        Use eagerload feature of sqlalchemy to optimize data retrieval for include querystring parameter.

        :params query: sqlalchemy queryset.
        :params qs: a querystring manager to retrieve information from url.
        :return: the query with includes eagerloaded.
        """
        pass

    def retrieve_object_query(
        self,
        view_kwargs: dict,
        filter_field: Any,
        filter_value: Any,
    ) -> QuerySet:
        """
        Build query to retrieve object.

        :params view_kwargs: kwargs from the resource view
        :params filter_field: the field to filter on
        :params filter_value: the value to filter with
        :return sqlalchemy query: a query from sqlalchemy
        """
        pass

    def query(self, view_kwargs: dict) -> QuerySet:
        """
        Construct the base query to retrieve wanted data.

        :params view_kwargs: kwargs from the resource view
        """
        return self.query_

    def before_create_object(self, data: dict, view_kwargs: dict):
        """
        Provide additional data before object creation.

        :params data: the data validated by marshmallow.
        :params view_kwargs: kwargs from the resource view.
        """
        pass

    def after_create_object(self, obj: Any, data: dict, view_kwargs: dict):
        """
        Provide additional data after object creation.

        :params obj: an object from data layer.
        :params data: the data validated by marshmallow.
        :params view_kwargs: kwargs from the resource view.
        """
        pass

    async def before_get_object(self, view_kwargs: dict):
        """
        Make work before to retrieve an object.

        :params view_kwargs: kwargs from the resource view.
        """
        pass

    async def after_get_object(self, obj: Any, view_kwargs: dict):
        """
        Make work after to retrieve an object.

        :params obj: an object from data layer.
        :params view_kwargs: kwargs from the resource view.
        """
        pass

    async def before_get_collection(self, qs: QueryStringManager, view_kwargs: dict):
        """
        Make work before to retrieve a collection of objects.

        :params qs: a querystring manager to retrieve information from url.
        :params view_kwargs: kwargs from the resource view.
        """
        pass

    async def after_get_collection(self, collection: Iterable, qs: QueryStringManager, view_kwargs: dict) -> Iterable:
        """
        Make work after to retrieve a collection of objects.

        :params collection: the collection of objects.
        :params qs: a querystring manager to retrieve information from url.
        :params view_kwargs: kwargs from the resource view.
        """
        return collection

    async def before_update_object(self, obj: Any, data: dict, view_kwargs: dict):
        """
        Make checks or provide additional data before update object.

        :params obj: an object from data layer.
        :params data: the data validated by pydantic.
        :params view_kwargs: kwargs from the resource view.
        """
        pass

    def after_update_object(self, obj: Any, data: dict, view_kwargs: dict):
        """
        Make work after update object.

        :params obj: an object from data layer.
        :params data: the data validated by pydantic.
        :params view_kwargs: kwargs from the resource view.
        """
        pass

    def before_delete_object(self, obj: Any, view_kwargs: dict):
        """
        Make checks before delete object.

        :params obj: an object from data layer.
        :params view_kwargs: kwargs from the resource view.
        """
        pass

    def after_delete_object(self, obj: Any, view_kwargs: dict):
        """
        Make work after delete object.

        :params obj: an object from data layer.
        :params view_kwargs: kwargs from the resource view.
        """
        pass

    def before_create_relationship(
        self,
        json_data: dict,
        relationship_field: str,
        related_id_field: str,
        view_kwargs: dict,
    ):
        """
        Make work before to create a relationship.

        :params json_data: the request params.
        :params relationship_field: the model attribute used for relationship.
        :params related_id_field: the identifier field of the related model.
        :params view_kwargs: kwargs from the resource view.
        :return boolean: True if relationship have changed else False.
        """
        pass

    def after_create_relationship(
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

        :params obj: an object from data layer.
        :params updated: True if object was updated else False.
        :params json_data: the request params.
        :params relationship_field: the model attribute used for relationship.
        :params related_id_field: the identifier field of the related model.
        :params view_kwargs: kwargs from the resource view.
        :return boolean: True if relationship have changed else False.
        """
        pass

    async def before_get_relationship(
        self,
        relationship_field: str,
        related_type_: str,
        related_id_field: str,
        view_kwargs: dict,
    ):
        """
        Make work before to get information about a relationship.

        :params str relationship_field: the model attribute used for relationship.
        :params str related_type_: the related resource type.
        :params str related_id_field: the identifier field of the related model.
        :params dict view_kwargs: kwargs from the resource view.
        :return tuple: the object and related object(s).
        """
        pass

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

        :params obj: an object from data layer.
        :params related_objects: related objects of the object.
        :params relationship_field: the model attribute used for relationship.
        :params related_type_: the related resource type.
        :params related_id_field: the identifier field of the related model.
        :params view_kwargs: kwargs from the resource view.
        :return tuple: the object and related object(s).
        """
        pass

    def before_update_relationship(
        self,
        json_data: dict,
        relationship_field: str,
        related_id_field: str,
        view_kwargs: dict,
    ):
        """
        Make work before to update a relationship.

        :params json_data: the request params.
        :params relationship_field: the model attribute used for relationship.
        :params related_id_field: the identifier field of the related model.
        :params view_kwargs: kwargs from the resource view.
        :return boolean: True if relationship have changed else False.
        """
        pass

    def after_update_relationship(
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

        :params obj: an object from data layer.
        :params updated: True if object was updated else False.
        :params json_data: the request params.
        :params relationship_field: the model attribute used for relationship.
        :params related_id_field: the identifier field of the related model.
        :params view_kwargs: kwargs from the resource view.
        :return boolean: True if relationship have changed else False.
        """
        pass

    def before_delete_relationship(
        self,
        json_data: dict,
        relationship_field: str,
        related_id_field: str,
        view_kwargs: dict,
    ):
        """
        Make work before to delete a relationship.

        :params json_data: the request params.
        :params relationship_field: the model attribute used for relationship.
        :params related_id_field: the identifier field of the related model.
        :params view_kwargs: kwargs from the resource view.
        """
        pass

    def after_delete_relationship(
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

        :params obj: an object from data layer.
        :params updated: True if object was updated else False.
        :params json_data: the request params.
        :params relationship_field: the model attribute used for relationship.
        :params related_id_field: the identifier field of the related model.
        :params view_kwargs: kwargs from the resource view.
        """
        pass
