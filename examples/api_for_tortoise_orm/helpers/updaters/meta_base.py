"""Base updaters module."""

from typing import (
    Any,
    Dict,
    Generic,
    Iterable,
    Optional,
    Type,
    TypeVar,
    Union,
)

from tortoise import models
from tortoise.exceptions import DoesNotExist

from fastapi_jsonapi.querystring import HeadersQueryStringManager

from .exceptions import (
    ExceptionBeforeUpdate,
    ExceptionNotUpdater,
    ObjectNotFound,
)

TYPE_VAR = TypeVar("TYPE_VAR")
TYPE_MODEL = TypeVar("TypeModel", bound=models.Model)


class _BaseUpdater(Generic[TYPE_MODEL]):
    class Meta(object):
        model: Any

    @classmethod
    async def update(
        cls,
        model_or_id: Union[TYPE_MODEL, int],
        new_data: Dict[str, Any],
        header: Union[HeadersQueryStringManager, None] = None,
        save: bool = True,
        update_fields: Optional[Iterable[str]] = None,
    ) -> TYPE_MODEL:
        """
        Create objects.

        :param cls: updater
        :param new_data: named parameters for the updater
        :param model_or_id: object or id
        :param header: header
        :param save: boolean flag: model saved to db or not
        :return: created model.
        """
        model_obj = await cls._preload_model(model_or_id)
        old_data = await model_obj.clone(pk=model_obj.id)  # type: ignore

        try:
            model_obj = await cls.before_update(obj=model_obj, new_data=new_data, header=header)
        except ExceptionBeforeUpdate:
            pass

        if save:
            await model_obj.save(update_fields=update_fields)

        return model_obj

    @classmethod
    async def _preload_model(cls, model_or_id: Union[TYPE_MODEL, int]) -> TYPE_MODEL:
        """
        Preload model method.

        If updater initialize with int id - load from database with this id.
        :return: Model. Returns model from initialization or preloaded model.
        :raises ObjectNotFound: if object does not found.
        """
        if isinstance(model_or_id, int):
            try:
                model = await cls.Meta.model.get(id=model_or_id)
            except DoesNotExist:
                raise ObjectNotFound(cls.Meta.model, description="Object does not exist")

            return model
        else:
            return model_or_id

    @classmethod
    async def before_update(
        cls,
        obj: TYPE_MODEL,
        new_data: Dict[Any, Any],
        header: Union[HeadersQueryStringManager, None] = None,
    ) -> TYPE_MODEL:
        """
        Perform logic before the updater starts.

        :param obj: argument with preloaded model,
        :param new_data: argument with new data
        :param header: header
        :return: named parameters to update an object
        :raises ExceptionBeforeUpdate: if 'before_update' has failed.
        """
        raise ExceptionBeforeUpdate


class Updaters(object):
    """Updaters factory."""

    _updaters: Dict[str, Type["_BaseUpdater"]] = dict()

    @classmethod
    def get(cls, name_model: str) -> Type["_BaseUpdater"]:
        """Get updater from storage."""
        try:
            return cls._updaters[name_model]
        except KeyError:
            raise ExceptionNotUpdater("Not found updater={model}".format(model=name_model))

    @classmethod
    def add(cls, name_updater: str, updater: Type["_BaseUpdater"]) -> None:
        """Add to storage method."""
        cls._updaters[name_updater] = updater


class MetaUpdater(type):
    """Metaclass for updater."""

    def __new__(cls, name, bases, attrs):
        """Create updater instance and add it to storage."""
        updater = super().__new__(cls, name, bases, attrs)
        if issubclass(updater, _BaseUpdater):
            Updaters.add(name, updater)
        return updater


class BaseUpdater(_BaseUpdater, metaclass=MetaUpdater):
    """Base updater."""

    ...
