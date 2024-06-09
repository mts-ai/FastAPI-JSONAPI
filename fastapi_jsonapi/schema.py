from __future__ import annotations

from inspect import isclass
from types import (
    GenericAlias,
    UnionType,
)
from typing import (
    TYPE_CHECKING,
    Union,
    get_args,
)

from pydantic import (
    BaseModel as PydanticBaseModel,
)
from pydantic import (
    ConfigDict,
    Field,
)
from pydantic._internal._typing_extra import is_none_type

from fastapi_jsonapi.common import search_relationship_info
from fastapi_jsonapi.schema_base import BaseModel

if TYPE_CHECKING:
    # noinspection PyProtectedMember
    from collections.abc import Sequence

    from fastapi import FastAPI
    from pydantic.fields import FieldInfo

    from fastapi_jsonapi.data_typing import TypeSchema


class BaseJSONAPIRelationshipSchema(BaseModel):
    id: str = Field(..., description="Related object ID")
    type: str = Field(..., description="Type of the related resource object")

    model_config = ConfigDict(extra="forbid")


class BaseJSONAPIRelationshipDataToOneSchema(BaseModel):
    data: BaseJSONAPIRelationshipSchema


class BaseJSONAPIRelationshipDataToManySchema(BaseModel):
    data: list[BaseJSONAPIRelationshipSchema]


class BaseJSONAPIItemSchema(BaseModel):
    """Base JSON:API item schema."""

    type: str = Field(description="Resource type")
    attributes: dict = Field(description="Resource object attributes")


class BaseJSONAPIItemInSchema(BaseJSONAPIItemSchema):
    """
    Schema for post/patch method

    TODO POST: optionally accept custom id for object https://jsonapi.org/format/#crud-creating-client-ids
    TODO PATCH: accept object id (maybe create a new separate schema)
    """

    attributes: TypeSchema = Field(description="Resource object attributes")
    relationships: TypeSchema | None = Field(None, description="Resource object relationships")
    id: str | None = Field(None, description="Resource object ID")


class BaseJSONAPIDataInSchema(BaseModel):
    data: BaseJSONAPIItemInSchema


class BaseJSONAPIObjectSchema(BaseJSONAPIItemSchema):
    """Base JSON:API object schema."""

    id: str = Field(description="Resource object ID")


class JSONAPIResultListMetaSchema(BaseModel):
    """JSON:API list meta schema."""

    count: int | None = None
    total_pages: int | None = Field(None, alias="totalPages")
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )


class JSONAPIDocumentObjectSchema(BaseModel):
    """
    JSON:API Document Object Schema.

    https://jsonapi.org/format/#document-jsonapi-object
    """

    version: str = Field(default="1.0", description="json-api версия")


class JSONAPIObjectSchema(BaseJSONAPIObjectSchema):
    """JSON:API base object schema."""


class BaseJSONAPIResultSchema(BaseModel):
    """JSON:API Required fields schema"""

    meta: JSONAPIResultListMetaSchema | None = Field(None, description="JSON:API metadata")
    jsonapi: JSONAPIDocumentObjectSchema = JSONAPIDocumentObjectSchema()


class JSONAPIResultListSchema(BaseJSONAPIResultSchema):
    """JSON:API list base result schema."""

    data: Sequence[JSONAPIObjectSchema] = Field(description="Resource objects collection")


class JSONAPIResultDetailSchema(BaseJSONAPIResultSchema):
    """JSON:API base detail schema."""

    data: JSONAPIObjectSchema = Field(description="Resource object data")


RelationshipInfoSchema = Union[
    type[BaseJSONAPIRelationshipDataToOneSchema],
    type[BaseJSONAPIRelationshipDataToManySchema],
]


class JSONAPISchemaIntrospectionError(Exception):
    pass


def get_model_field(schema: type[TypeSchema], field: str) -> str:
    """
    Get the model field of a schema field.

    # todo: use alias (custom names)?
       For example:

    class Computer(sqla_base):
        user = relationship(User)

    class ComputerSchema(pydantic_base):
        owner = Field(alias="user", relationship=...)

    :param schema: a pydantic schema
    :param field: the name of the schema field
    :return: the name of the field in the model
    :raises Exception: if the schema from parameter has no attribute for parameter.
    """
    if schema.model_fields.get(field) is None:
        msg = f"{schema.__name__} has no attribute {field}"
        raise JSONAPISchemaIntrospectionError(msg)
    return field


def get_relationship_fields_names(
    schema: type[TypeSchema],
) -> set[str]:
    """
    Return relationship fields of a schema.

    :param schema: a schemas schema
    """
    names: set[str] = set()
    for i_name, i_type in schema.model_fields.items():
        if search_relationship_info.first(i_type):
            names.add(i_name)

    return names


def get_schema_from_type(resource_type: str, app: FastAPI) -> type[BaseModel]:
    """
    Retrieve a schema from the registry by his type.

    :param resource_type: the type of the resource.
    :param app: FastAPI app instance.
    :return Schema: the schema class.
    :raises Exception: if the schema not found for this resource type.
    """
    schemas: dict[str, type[BaseModel]] = getattr(app, "schemas", {})
    try:
        return schemas[resource_type]
    except KeyError:
        msg = f"Couldn't find schema for type: {resource_type}"
        raise ValueError(msg)


def get_schema_from_field_annotation(field: FieldInfo) -> type[BaseModel] | None:
    """TODO: consider using pydantic's GenerateSchema ?"""
    choices = []
    if isinstance(field.annotation, UnionType):
        args = get_args(field.annotation)
        choices.extend(args)
    else:
        choices.append(field.annotation)
    while choices:
        elem = choices.pop(0)
        if isinstance(elem, GenericAlias):
            choices.extend(get_args(elem))
            continue

        if is_none_type(elem):
            continue

        if isclass(elem) and issubclass(elem, PydanticBaseModel):
            return elem

    return None


def get_related_schema(schema: type[TypeSchema], field: str) -> type[TypeSchema]:
    """
    Retrieve the related schema of a relationship field.

    :params schema: the schema to retrieve le relationship field from
    :params field: the relationship field
    :return: the related schema
    """
    return get_schema_from_field_annotation(schema.model_fields[field])
