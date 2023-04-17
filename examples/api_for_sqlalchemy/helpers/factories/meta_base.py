"""Base factory module."""

from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_jsonapi.data_layers.fields.enum import Enum
from .exceptions import (
    ExceptionAfterCommit,
    ExceptionBeforeCreate,
    ExceptionNotFactory, ErrorCreateObject,
)
from fastapi_jsonapi.querystring import HeadersQueryStringManager
from ...extensions.sqlalchemy import Base

TypeModel = TypeVar("TypeModel", bound=Base)


class FactoryUseMode(Enum):
    """Effects the creation of an object in a factory. In test mode data generated randomly."""

    test = 1  # for tests, that is, data is generated randomly (unless specified explicitly)
    production = 2  # working version, you can not allow random data generation


class _BaseFactory(Generic[TypeModel]):
    class Meta(object):
        model: Type[TypeModel]

    data: Dict[str, Callable] = {}
    """simple data like text, dict and etc."""
    awaitable_data: Dict[str, Tuple[Callable, List, Dict]] = {}
    """awaitable with arguments (like another factory)
    Usage:
    awaitable_data = {
        'attribute_name': (lambda: Factories.get("example_factory").create, [<args_list>], {<kwargs_dict>}),
    }
    Warning!!! lambda function is required!
    """

    @classmethod
    async def _get_data(cls, data: Optional[Dict[str, Any]] = None, mode: FactoryUseMode = FactoryUseMode.test) -> Dict:
        new_kwargs = dict()
        if data:
            new_kwargs.update(data)

        if mode is FactoryUseMode.test:
            for name, val in cls.data.items():
                if name not in new_kwargs:
                    new_kwargs[name] = val()
            for name, awaitable_pack in cls.awaitable_data.items():
                if name not in new_kwargs:
                    lambda_func, f_args, f_kwargs = awaitable_pack
                    new_kwargs[name] = await lambda_func()(*f_args, **f_kwargs)
        return new_kwargs

    @classmethod
    async def create_batch(
        cls,
        count: int = 1,
        data: Optional[Dict[str, Any]] = None,
        save: bool = True,
        mode: FactoryUseMode = FactoryUseMode.test,
    ) -> List[Base]:
        """
        Create objects.

        :param cls: factory
        :param count: you can pass an optional parameter - the number of instances, default = 1
        :param data: named parameters for the factory
        :param save: flag save model to db or not (save by default)
        :param mode: what is the factory used for
        :return: new object.
        """
        result_data = []
        for step in range(1, count + 1):
            new_kwargs = await cls._get_data(data=data, mode=mode)
            try:
                new_kwargs = await cls.before_create(many=True, mode=mode, model_kwargs=new_kwargs)
            except ExceptionBeforeCreate:
                pass
            new_object = cls.Meta.model(**new_kwargs)
            if save:
                await new_object.save()
            result_data.append(new_object)

        try:
            await cls.after_create(result_data=result_data, many=True, saved=save, mode=mode)
        except ExceptionAfterCommit:
            pass

        return result_data

    @classmethod
    async def create(
        cls,
        data: Optional[Dict[str, Any]] = None,
        header: Union[HeadersQueryStringManager, None] = None,
        save: bool = True,
        mode: FactoryUseMode = FactoryUseMode.test,
        session: Optional[AsyncSession] = None,
    ) -> Base:
        """
        Create objects.

        :param cls: factory
        :param data: named parameters for the factory
        :param header: header
        :param save: flag save model to db or not (save by default)
        :param mode: what is the factory used for
        :param session:
        :return: created model.
        """
        new_kwargs = await cls._get_data(data=data, mode=mode)

        try:
            new_kwargs = await cls.before_create(many=False, mode=mode, model_kwargs=new_kwargs, header=header)
        except ExceptionBeforeCreate:
            pass

        result_data = cls.Meta.model(**new_kwargs)
        if save:
            if session:
                session.add(result_data)
                await session.commit()
            else:
                await result_data.save()

        try:
            await cls.after_create(result_data=result_data, many=False, saved=save, mode=mode, header=header)
        except ExceptionAfterCommit:
            pass

        return result_data

    @classmethod
    async def before_create(
        cls,
        many: bool,
        mode: FactoryUseMode,
        model_kwargs: Dict,
        header: Union[HeadersQueryStringManager, None] = None,
    ) -> Dict:
        """
        Perform logic before the factory starts.

        :param many: boolean flag: bulk save or not
        :param mode: Factory mode
        :param model_kwargs: argument which pass to fabric
        :param header: header
        :return: named parameters to create an object
        :raises ExceptionBeforeCreate: if 'before_create' has failed.
        """
        raise ExceptionBeforeCreate

    @classmethod
    async def after_create(
        cls,
        result_data: Union[List[TypeModel], TypeModel],
        many: bool,
        saved: bool,
        mode: FactoryUseMode,
        header: Union[HeadersQueryStringManager, None] = None,
    ) -> None:
        """
        Perform logic after data.

        :param result_data: created object
        :param many: boolean flag: bulk save or not
        :param saved: boolean flag: model saved to db or not
        :param mode: Factory mode
        :param header: header
        :raises ExceptionAfterCommit: if 'after_create' has failed.
        """
        raise ExceptionAfterCommit

    @classmethod
    async def _prepare_attribute_or_raise(
        cls,
        field_name: str,
        data_for_create: Dict[str, Any],
        kwargs: Dict[str, Any],
    ) -> None:
        value_for_create = kwargs.get(field_name)
        if value_for_create is None:
            raise ErrorCreateObject(
                model=cls.Meta.model,
                description=f'field required {field_name!r}',
                field=field_name,
            )
        data_for_create[field_name] = value_for_create


class Factories:
    """Хранилище фабрик."""

    _factories: Dict[str, Type["_BaseFactory"]] = dict()

    @classmethod
    def get(cls, name_model: str) -> Type["_BaseFactory"]:
        """
        Get factory for model.

        :param name_model: str.
        :return: factory for model.
        :raises ExceptionNotFactory: if no factory is found for this model.
        """
        factory = cls._factories.get(name_model)
        if factory is None:
            raise ExceptionNotFactory("Not found factory={model}".format(model=name_model))
        return factory

    @classmethod
    def add(cls, name_factory: str, factory: Type["_BaseFactory"]) -> None:
        """Add new factory to storage."""
        cls._factories[name_factory] = factory


class MetaFactory(type):
    """Factory meta class."""

    def __new__(cls, name, bases, attrs):
        """Add new factory to factories storage."""
        factory = super().__new__(cls, name, bases, attrs)
        if issubclass(factory, _BaseFactory):
            Factories.add(name, factory)
        return factory


class BaseFactory(_BaseFactory, metaclass=MetaFactory):
    """Base factory."""

    ...


TypeBaseFactory = TypeVar('TypeBaseFactory', bound=BaseFactory)  # type: ignore


def factory_import(name: str) -> Type[TypeBaseFactory]:
    components = name.split('.')
    mod = __import__('.'.join(components[:-1]))  # noqa: WPS421
    for comp in components[1:]:
        mod = getattr(mod, comp)
    # TODO Починить при помощи regisry тк такой импорт замедляет
    #  работу фабрик которые требуют вызовы других фабрик
    return mod  # type: ignore


async def create_from_factory(factory: str, **kwargs: Union[Any]) -> TypeModel:
    factory_clss: Type[BaseFactory[TypeModel]] = factory_import(factory)
    return await factory_clss(**kwargs).create()

