"""
Base JSON:API schemas.
Pydantic (for FastAPI).
"""
from typing import (
    Dict,
    Type,
    List,
    Optional,
    Sequence,
    TYPE_CHECKING,
    Union,
)

from fastapi import FastAPI
from fastapi.openapi.utils import get_flat_models_from_routes

from pydantic import (
    BaseModel,
    Field,
)

if TYPE_CHECKING:
    from fastapi_rest_jsonapi.data_layers.data_typing import TypeSchema


class BaseJSONAPIRelationshipSchema(BaseModel):
    id: str = Field(..., description="Related object ID")
    type: str = Field(..., description="Type of the related resource object")


class BaseJSONAPIRelationshipDataToOneSchema(BaseModel):
    data: BaseJSONAPIRelationshipSchema


class BaseJSONAPIRelationshipDataToManySchema(BaseModel):
    data: List[BaseJSONAPIRelationshipSchema]


class BaseJSONAPIItemSchema(BaseModel):
    """Base JSON:API item schema."""

    type: str = Field(description="Resource type")
    attributes: dict = Field(description="Resource object attributes")


class BasePostJSONAPISchema(BaseJSONAPIItemSchema):
    """Base POST JSON:API schema."""


class BaseJSONAPIObjectSchema(BaseJSONAPIItemSchema):
    """Base JSON:API object schema."""

    id: str = Field(description="Resource object ID")


class BasePatchJSONAPISchema(BaseJSONAPIObjectSchema):
    """Base PATCH JSON:API schema."""


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


class BasicPipelineActionSchema(BaseModel):
    """Action schema."""

    name: str = Field(default="Default name", description="Человекочитаемое название параметра")
    type: str = Field(default="int", description="Type of a variable")
    var: str = Field(default="default_var", description="Переменная для разработчика")
    operation: List[str] = Field(default=["eq"], description="List of permitted operations")


class StringSchema(BasicPipelineActionSchema):
    """String parameter schema."""

    name: str = Field(default="Текст 1")
    type: str = Field(default="str", const=True)
    operation: List[str] = Field(
        default=[
            "eq",
            "ne",
            "any",
            "endswith",
            "ilike",
            "in_",
            "like",
            "match",
            "notilike",
            "notlike",
            "notin_",
            "startswith",
        ],
        const=True,
    )

    class Meta:
        """String parameter schema."""

        type = str


class IntSchema(BasicPipelineActionSchema):
    """Int parameter schema."""

    name: str = Field(default="Число 1")
    type: str = Field(default="int", const=True)
    operation: List[str] = Field(default=["eq", "ne", "gt", "ge", "in_", "lt", "le", "notin_"], const=True)

    class Meta:
        """Int parameter meta."""

        type = int


class FloatSchema(BasicPipelineActionSchema):
    """Float parameter schema."""

    name: str = Field(default="Процент 1")
    type: str = Field(default="float", const=True)
    operation: List[str] = Field(default=["eq", "ne", "gt", "ge", "in_", "lt", "le", "notin_"], const=True)

    class Meta:
        """Float parameter schema."""

        type = float


class BoolSchema(BasicPipelineActionSchema):
    """Boolean action schema."""

    name: str = Field(default="Детектор сработал на событие Х")
    type: str = Field(default="bool", const=True)
    operation: List[str] = Field(default=["eq", "is_", "ne"], const=True)

    class Meta:
        """Boolean parameter meta."""

        type = bool


def get_model_field(schema: Type["TypeSchema"], field: str) -> str:
    """
    Get the model field of a schema field.

    :param schema: a pydantic schema
    :param field: the name of the schema field
    :return: the name of the field in the model
    :raises Exception: if the schema from parameter has no attribute for parameter.
    """
    if schema.__fields__.get(field) is None:
        raise Exception("{schema} has no attribute {field}".format(schema=schema.__name__, field=field))
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
        raise Exception("Couldn't find schema for type: {type}".format(type=resource_type))


def collect_app_orm_schemas(app: FastAPI) -> None:
    """
    Collect schemas if it has Config->model attributes.

    Need for JSON_API.
    :param app: FastAPI instance
    :return: nothing
    """
    models_dict: Dict[str, Type[BaseModel]] = {}
    flat_models = get_flat_models_from_routes(app.routes)
    for model in flat_models:
        if not hasattr(model, "Config"):
            continue
        model_type = getattr(getattr(model, "Config"), "model", None)
        if model_type:
            if model_type in models_dict:
                raise RuntimeError(
                    "Get duplication value of Config.model={name} for schema={model}. Duplicate in {model_copy}".format(
                        name=model_type, model=model.__name__, model_copy=models_dict[model_type].__name__
                    )
                )
            models_dict[model_type] = model
    if models_dict:
        setattr(app, "schemas", models_dict)


def get_related_schema(schema: Type["TypeSchema"], field: str) -> Type["TypeSchema"]:
    """
    Retrieve the related schema of a relationship field.

    :params schema: the schema to retrieve le relationship field from
    :params field: the relationship field
    :return: the related schema
    """
    return schema.__fields__[field].type_
