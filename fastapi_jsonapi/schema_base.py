__all__ = (
    "Field",
    "BaseModel",
    "registry",
    "RelationshipInfo",
)

from typing import Dict

from pydantic import BaseModel as BaseModelGeneric
from pydantic import Field
from pydantic.main import ModelMetaclass


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


class RegistryMeta(ModelMetaclass):
    def __new__(mcs, *args, **kwargs):
        # any other way to get all known schemas?
        schema = super().__new__(mcs, *args, **kwargs)
        registry.add(schema)
        return schema


class BaseModel(BaseModelGeneric, metaclass=RegistryMeta):
    pass


class RelationshipInfo(BaseModel):
    resource_type: str
    many: bool = False
    related_view: str = None
    related_view_kwargs: Dict[str, str] = Field(default_factory=dict)
    resource_id_example: str = "1"
    id_field_name: str = "id"

    # TODO: Pydantic V2 use model_config
    class Config:
        frozen = True
