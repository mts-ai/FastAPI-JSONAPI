__all__ = (
    "Field",
    "BaseModel",
    "registry",
)

from pydantic import BaseModel as BaseModelGeneric
from pydantic import Field


class Registry:
    def __init__(self):
        self._known = {}

    def add(self, schema):
        self._known[schema.__name__] = schema

    def get(self, name: str):
        return self._known.get(name)

    @property
    def schemas(self):
        return dict(self._known)


registry = Registry()


class RegistryMeta(BaseModelGeneric):
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        registry.add(cls)


class BaseModel(RegistryMeta):
    pass
