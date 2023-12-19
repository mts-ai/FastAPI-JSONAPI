"""
Base JSON:API schemas.

Pydantic (for FastAPI).
"""
from typing import (
    TYPE_CHECKING,
    Dict,
    List,
    Optional,
    Sequence,
    Type,
    Union,
)

from fastapi import FastAPI
from pydantic import (
    BaseConfig,
    BaseModel,
    Extra,
    Field,
)

if TYPE_CHECKING:
    from fastapi_jsonapi.data_typing import TypeSchema


class BaseJSONAPIRelationshipSchema(BaseModel):
    id: str = Field(..., description="Related object ID")
    type: str = Field(..., description="Type of the related resource object")

    class Config(BaseConfig):
        extra = Extra.forbid


class BaseJSONAPIRelationshipDataToOneSchema(BaseModel):
    data: BaseJSONAPIRelationshipSchema


class BaseJSONAPIRelationshipDataToManySchema(BaseModel):
    data: List[BaseJSONAPIRelationshipSchema]


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

    attributes: "TypeSchema" = Field(description="Resource object attributes")
    relationships: Optional["TypeSchema"] = Field(None, description="Resource object relationships")
    id: Optional[str] = Field(description="Resource object ID")


class BaseJSONAPIDataInSchema(BaseModel):
    data: BaseJSONAPIItemInSchema


class BaseJSONAPIObjectSchema(BaseJSONAPIItemSchema):
    """Base JSON:API object schema."""

    id: str = Field(description="Resource object ID")


class JSONAPIResultListMetaSchema(BaseModel):
    """JSON:API list meta schema."""

    count: Optional[int]
    total_pages: Optional[int] = Field(alias="totalPages")

    class Config:
        allow_population_by_field_name = True


class JSONAPIDocumentObjectSchema(BaseModel):
    """
    JSON:API Document Object Schema.

    https://jsonapi.org/format/#document-jsonapi-object
    """

    version: str = Field(default="1.0", description="json-api версия")


class JSONAPIObjectSchema(BaseJSONAPIObjectSchema):
    """JSON:API base object schema."""


class BaseJSONAPIResultSchema(BaseModel):
    """
    JSON:API Required fields schema
    """

    meta: Optional[JSONAPIResultListMetaSchema] = Field(description="JSON:API metadata")
    jsonapi: JSONAPIDocumentObjectSchema = JSONAPIDocumentObjectSchema()


class JSONAPIResultListSchema(BaseJSONAPIResultSchema):
    """JSON:API list base result schema."""

    data: Sequence[JSONAPIObjectSchema] = Field(description="Resource objects collection")


class JSONAPIResultDetailSchema(BaseJSONAPIResultSchema):
    """JSON:API base detail schema."""

    data: JSONAPIObjectSchema = Field(description="Resource object data")


RelationshipInfoSchema = Union[
    Type[BaseJSONAPIRelationshipDataToOneSchema],
    Type[BaseJSONAPIRelationshipDataToManySchema],
]


def get_model_field(schema: Type["TypeSchema"], field: str) -> str:
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
    if schema.__fields__.get(field) is None:
        msg = "{schema} has no attribute {field}".format(
            schema=schema.__name__,
            field=field,
        )
        raise Exception(msg)
    return field


def get_relationships(schema: Type["TypeSchema"], model_field: bool = False) -> List[str]:
    """
    Return relationship fields of a schema.

    :param schema: a schemas schema
    :param model_field: list of relationship fields of a schema
    """
    relationships: List[str] = []
    for i_name, i_type in schema.__fields__.items():
        try:
            if issubclass(i_type.type_, BaseModel):
                relationships.append(i_name)
        except TypeError:
            pass

    if model_field is True:
        relationships = [get_model_field(schema, key) for key in relationships]

    return relationships


def get_schema_from_type(resource_type: str, app: FastAPI) -> Type[BaseModel]:
    """
    Retrieve a schema from the registry by his type.

    :param resource_type: the type of the resource.
    :param app: FastAPI app instance.
    :return Schema: the schema class.
    :raises Exception: if the schema not found for this resource type.
    """
    schemas: Dict[str, Type[BaseModel]] = getattr(app, "schemas", {})
    try:
        return schemas[resource_type]
    except KeyError:
        msg = "Couldn't find schema for type: {type}".format(type=resource_type)
        raise Exception(msg)


def get_related_schema(schema: Type["TypeSchema"], field: str) -> Type["TypeSchema"]:
    """
    Retrieve the related schema of a relationship field.

    :params schema: the schema to retrieve le relationship field from
    :params field: the relationship field
    :return: the related schema
    """
    return schema.__fields__[field].type_
