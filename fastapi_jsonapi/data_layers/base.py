"""
The base class of a data layer.
If you want to create your own data layer
you must inherit from this base class
"""

import types
from typing import List, Optional, Tuple, Type

from fastapi_jsonapi.data_typing import TypeModel, TypeSchema
from fastapi_jsonapi.querystring import QueryStringManager
from fastapi_jsonapi.schema import BaseJSONAPIItemInSchema


class BaseDataLayer:
    """Base class of a data layer"""

    REWRITABLE_METHODS = (
        "query",
        "before_create_object",
        "after_create_object",
        "before_get_object",
        "after_get_object",
        "before_get_collection",
        "after_get_collection",
        "before_update_object",
        "after_update_object",
        "before_delete_object",
        "after_delete_object",
        "before_create_relationship",
        "after_create_relationship",
        "before_get_relationship",
        "after_get_relationship",
        "before_update_relationship",
        "after_update_relationship",
        "before_delete_relationship",
        "after_delete_relationship",
        "retrieve_object_query",
    )

    def __init__(
        self,
        schema: Type[TypeSchema],
        model: Type[TypeModel],
        url_id_field: str,
        id_name_field: Optional[str] = None,
        disable_collection_count: bool = False,
        default_collection_count: int = -1,
        **kwargs,
    ):
        """
        :param schema:
        :param model:
        :param url_id_field:
        :param id_name_field:
        :param disable_collection_count:
        :param default_collection_count:
        :param kwargs:
        """
        self.model = model
        self.schema = schema
        self.url_id_field = url_id_field
        self.id_name_field = id_name_field
        self.disable_collection_count: bool = disable_collection_count
        self.default_collection_count: int = default_collection_count

    async def create_object(self, data_create: BaseJSONAPIItemInSchema, view_kwargs: dict) -> TypeModel:
        """
        Create an object

        :param data_create: validated data
        :param view_kwargs: kwargs from the resource view
        :return DeclarativeMeta: an object
        """
        raise NotImplementedError

    def get_object_id_field_name(self):
        """
        compound key may cause errors
        :return:
        """
        return self.id_name_field

    def get_object_id_field(self):
        id_name_field = self.get_object_id_field_name()
        try:
            return getattr(self.model, id_name_field)
        except AttributeError:
            msg = f"{self.model.__name__} has no attribute {id_name_field}"
            # TODO: any custom exception type?
            raise Exception(msg)

    async def get_object(self, view_kwargs: dict, qs: Optional[QueryStringManager] = None) -> TypeModel:
        """
        Retrieve an object

        :param view_kwargs: kwargs from the resource view
        :param qs:
        :return DeclarativeMeta: an object
        """
        raise NotImplementedError

    async def get_collection(self, qs: QueryStringManager, view_kwargs: Optional[dict] = None) -> Tuple[int, list]:
        """
        Retrieve a collection of objects

        :param qs: a querystring manager to retrieve information from url
        :param view_kwargs: kwargs from the resource view
        :return tuple: the number of object and the list of objects
        """
        raise NotImplementedError

    async def update_object(self, obj, data_update: BaseJSONAPIItemInSchema, view_kwargs: dict):
        """
        Update an object

        :param obj: an object
        :param data_update: the data validated by schemas
        :param view_kwargs: kwargs from the resource view
        :return boolean: True if object have changed else False
        """
        # TODO: update doc
        raise NotImplementedError

    async def delete_object(self, obj, view_kwargs):
        """
        Delete an item through the data layer

        :param DeclarativeMeta obj: an object
        :param view_kwargs: kwargs from the resource view
        """
        raise NotImplementedError

    async def create_relationship(
        self,
        json_data,
        relationship_field,
        related_id_field,
        view_kwargs,
    ):
        """
        Create a relationship

        :param json_data: the request params
        :param str relationship_field: the model attribute used for relationship
        :param str related_id_field: the identifier field of the related model
        :param view_kwargs: kwargs from the resource view
        :return boolean: True if relationship have changed else False
        """
        raise NotImplementedError

    async def get_relationship(
        self,
        relationship_field,
        related_type_,
        related_id_field,
        view_kwargs,
    ):
        """
        Get information about a relationship

        :param str relationship_field: the model attribute used for relationship
        :param str related_type_: the related resource type
        :param str related_id_field: the identifier field of the related model
        :param view_kwargs: kwargs from the resource view
        :return tuple: the object and related object(s)
        """
        raise NotImplementedError

    async def update_relationship(
        self,
        json_data,
        relationship_field,
        related_id_field,
        view_kwargs,
    ):
        """
        Update a relationship

        :param json_data: the request params
        :param str relationship_field: the model attribute used for relationship
        :param str related_id_field: the identifier field of the related model
        :param view_kwargs: kwargs from the resource view
        :return boolean: True if relationship have changed else False
        """
        raise NotImplementedError

    async def delete_relationship(
        self,
        json_data,
        relationship_field,
        related_id_field,
        view_kwargs,
    ):
        """
        Delete a relationship

        :param json_data: the request params
        :param str relationship_field: the model attribute used for relationship
        :param str related_id_field: the identifier field of the related model
        :param view_kwargs: kwargs from the resource view
        """
        raise NotImplementedError

    async def get_related_object(
        self,
        related_model: Type[TypeModel],
        related_id_field: str,
        id_value: str,
    ) -> TypeModel:
        """
        Get related object.

        :param related_model: Related ORM model class (not instance)
        :param related_id_field: id field of the related model (usually it's `id`)
        :param id_value: related object id value
        :return: an ORM object
        """
        raise NotImplementedError

    async def get_related_objects_list(
        self,
        related_model: Type[TypeModel],
        related_id_field: str,
        ids: list[str],
    ) -> list[TypeModel]:
        """
        Get related objects list.

        :param related_model: Related ORM model class (not instance)
        :param related_id_field: id field of the related model (usually it's `id`)
        :param ids: related object id values list
        :return: a list of ORM objects
        """
        raise NotImplementedError

    def query(self, view_kwargs):
        """
        Construct the base query to retrieve wanted data

        :param view_kwargs: kwargs from the resource view
        """
        raise NotImplementedError

    async def before_create_object(self, data, view_kwargs):
        """
        Provide additional data before object creation

        :param data: the data validated by schemas
        :param view_kwargs: kwargs from the resource view
        """
        raise NotImplementedError

    async def after_create_object(self, obj, data, view_kwargs):
        """
        Provide additional data after object creation

        :param obj: an object from data layer
        :param data: the data validated by schemas
        :param view_kwargs: kwargs from the resource view
        """
        raise NotImplementedError

    async def before_get_object(self, view_kwargs):
        """
        Make work before to retrieve an object

        :param view_kwargs: kwargs from the resource view
        """
        raise NotImplementedError

    async def after_get_object(self, obj, view_kwargs):
        """
        Make work after to retrieve an object

        :param obj: an object from data layer
        :param view_kwargs: kwargs from the resource view
        """
        raise NotImplementedError

    async def before_get_collection(self, qs, view_kwargs):
        """
        Make work before to retrieve a collection of objects

        :param qs: a querystring manager to retrieve information from url
        :param view_kwargs: kwargs from the resource view
        """
        raise NotImplementedError

    async def after_get_collection(self, collection, qs, view_kwargs):
        """
        Make work after to retrieve a collection of objects

        :param iterable collection: the collection of objects
        :param qs: a querystring manager to retrieve information from url
        :param view_kwargs: kwargs from the resource view
        """
        raise NotImplementedError

    async def before_update_object(self, obj, data, view_kwargs):
        """
        Make checks or provide additional data before update object

        :param obj: an object from data layer
        :param data: the data validated by schemas
        :param view_kwargs: kwargs from the resource view
        """
        raise NotImplementedError

    async def after_update_object(self, obj: TypeModel, data, view_kwargs):
        """
        Make work after update object

        :param obj: an object from data layer
        :param data: the data validated by schemas
        :param view_kwargs: kwargs from the resource view
        """
        raise NotImplementedError

    async def before_delete_object(self, obj: TypeModel, view_kwargs):
        """
        Make checks before delete object

        :param obj: an object from data layer
        :param view_kwargs: kwargs from the resource view
        """
        raise NotImplementedError

    async def after_delete_object(self, obj: TypeModel, view_kwargs):
        """
        Make work after delete object

        :param obj: an object from data layer
        :param view_kwargs: kwargs from the resource view
        """
        raise NotImplementedError

    async def delete_objects(self, objects: List[TypeModel], view_kwargs):
        # TODO: doc
        raise NotImplementedError

    async def before_delete_objects(self, objects: List[TypeModel], view_kwargs: dict):
        """
        Make checks before deleting objects.

        :param objects: an object from data layer.
        :param view_kwargs: kwargs from the resource view.
        """
        pass

    async def after_delete_objects(self, objects: List[TypeModel], view_kwargs: dict):
        """
        Any action after deleting objects.

        :param objects: an object from data layer.
        :param view_kwargs: kwargs from the resource view.
        """
        pass

    async def before_create_relationship(
        self,
        json_data,
        relationship_field,
        related_id_field,
        view_kwargs,
    ):
        """
        Make work before to create a relationship

        :param json_data: the request params
        :param str relationship_field: the model attribute used for relationship
        :param str related_id_field: the identifier field of the related model
        :param view_kwargs: kwargs from the resource view
        :return boolean: True if relationship have changed else False
        """
        raise NotImplementedError

    async def after_create_relationship(
        self,
        obj,
        updated,
        json_data,
        relationship_field,
        related_id_field,
        view_kwargs,
    ):
        """
        Make work after to create a relationship

        :param obj: an object from data layer
        :param bool updated: True if object was updated else False
        :param json_data: the request params
        :param str relationship_field: the model attribute used for relationship
        :param str related_id_field: the identifier field of the related model
        :param view_kwargs: kwargs from the resource view
        :return boolean: True if relationship have changed else False
        """
        raise NotImplementedError

    async def before_get_relationship(
        self,
        relationship_field,
        related_type_,
        related_id_field,
        view_kwargs,
    ):
        """
        Make work before to get information about a relationship

        :param str relationship_field: the model attribute used for relationship
        :param str related_type_: the related resource type
        :param str related_id_field: the identifier field of the related model
        :param view_kwargs: kwargs from the resource view
        :return tuple: the object and related object(s)
        """
        raise NotImplementedError

    async def after_get_relationship(
        self,
        obj,
        related_objects,
        relationship_field,
        related_type_,
        related_id_field,
        view_kwargs,
    ):
        """
        Make work after to get information about a relationship

        :param obj: an object from data layer
        :param iterable related_objects: related objects of the object
        :param str relationship_field: the model attribute used for relationship
        :param str related_type_: the related resource type
        :param str related_id_field: the identifier field of the related model
        :param view_kwargs: kwargs from the resource view
        :return tuple: the object and related object(s)
        """
        raise NotImplementedError

    async def before_update_relationship(
        self,
        json_data,
        relationship_field,
        related_id_field,
        view_kwargs,
    ):
        """
        Make work before to update a relationship

        :param json_data: the request params
        :param str relationship_field: the model attribute used for relationship
        :param str related_id_field: the identifier field of the related model
        :param view_kwargs: kwargs from the resource view
        :return boolean: True if relationship have changed else False
        """
        raise NotImplementedError

    async def after_update_relationship(
        self,
        obj,
        updated,
        json_data,
        relationship_field,
        related_id_field,
        view_kwargs,
    ):
        """
        Make work after to update a relationship

        :param obj: an object from data layer
        :param bool updated: True if object was updated else False
        :param json_data: the request params
        :param str relationship_field: the model attribute used for relationship
        :param str related_id_field: the identifier field of the related model
        :param view_kwargs: kwargs from the resource view
        :return boolean: True if relationship have changed else False
        """
        raise NotImplementedError

    async def before_delete_relationship(
        self,
        json_data,
        relationship_field,
        related_id_field,
        view_kwargs,
    ):
        """
        Make work before to delete a relationship

        :param json_data: the request params
        :param str relationship_field: the model attribute used for relationship
        :param str related_id_field: the identifier field of the related model
        :param view_kwargs: kwargs from the resource view
        """
        raise NotImplementedError

    async def after_delete_relationship(
        self,
        obj,
        updated,
        json_data,
        relationship_field,
        related_id_field,
        view_kwargs,
    ):
        """
        Make work after to delete a relationship

        :param obj: an object from data layer
        :param bool updated: True if object was updated else False
        :param json_data: the request params
        :param str relationship_field: the model attribute used for relationship
        :param str related_id_field: the identifier field of the related model
        :param view_kwargs: kwargs from the resource view
        """
        raise NotImplementedError

    def bound_rewritable_methods(self, methods):
        """
        Bound additional methods to current instance

        :param class methods: methods
        """
        for key, value in methods.items():
            if key in self.REWRITABLE_METHODS:
                setattr(self, key, types.MethodType(value, self))
