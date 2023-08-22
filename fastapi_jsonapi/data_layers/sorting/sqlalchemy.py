"""Helper to create sqlalchemy sortings according to filter querystring parameter"""
from typing import Any, List, Tuple, Type, Union

from pydantic.fields import ModelField
from sqlalchemy.orm import DeclarativeMeta, InstrumentedAttribute, aliased
from sqlalchemy.sql.elements import BinaryExpression

from fastapi_jsonapi.data_layers.shared import create_filters_or_sorts
from fastapi_jsonapi.data_typing import TypeModel, TypeSchema
from fastapi_jsonapi.exceptions import InvalidFilters, InvalidSort
from fastapi_jsonapi.schema import get_model_field, get_relationships
from fastapi_jsonapi.splitter import SPLIT_REL
from fastapi_jsonapi.utils.sqla import get_related_model_cls

Sort = BinaryExpression
Join = List[Any]

SortAndJoins = Tuple[
    Sort,
    List[Join],
]


def create_sorts(model: Type[TypeModel], filter_info: Union[list, dict], schema: Type[TypeSchema]):
    """
    Apply filters from filters information to base query.

    :params model: the model of the node.
    :params filter_info: current node filter information.
    :params schema: the resource.
    """
    return create_filters_or_sorts(model, filter_info, Node, schema)


class Node(object):
    """Helper to recursively create sorts with sqlalchemy according to sort querystring parameter"""

    def __init__(self, model: Type[TypeModel], sort_: dict, schema: Type[TypeSchema]):
        """
        Initialize an instance of a filter node.

        :params model: an sqlalchemy model.
        :params sort_: sorts information of the current node and deeper nodes.
        :param schema: the serializer of the resource.
        """
        self.model = model
        self.sort_ = sort_
        self.schema = schema

    @classmethod
    def create_sort(cls, schema_field: ModelField, model_column, order: str):
        """
        Create sqlalchemy sort.

        :params schema_field:
        :params model_column: column sqlalchemy
        :params order: desc | asc (or custom)
        :return:
        """
        """
        Custom sqlachemy sorting logic can be created in a marshmallow field for any field
        You can override existing ('asc', 'desc') or create new - then follow this pattern:
        `_<custom_sort_name>_sql_sort_`. This method has to accept following params:
        * marshmallow_field - marshmallow field instance
        * model_column - sqlalchemy column instance
        """
        try:
            f = getattr(schema_field, f"_{order}_sql_sort_")
        except AttributeError:
            pass
        else:
            return f(
                schema_field=schema_field,
                model_column=model_column,
            )
        return getattr(model_column, order)()

    def resolve(self) -> SortAndJoins:
        """
        Create sort for a particular node of the sort tree.
        """
        field = self.sort_.get("field", "")
        if not hasattr(self.model, field) and SPLIT_REL not in field:
            msg = "{} has no attribute {}".format(self.model.__name__, field)
            raise InvalidSort(msg)

        if SPLIT_REL in field:
            value = {"field": SPLIT_REL.join(field.split(SPLIT_REL)[1:]), "order": self.sort_["order"]}
            alias = aliased(self.related_model)
            joins = [[alias, self.column]]
            node = Node(alias, value, self.related_schema)
            filters, new_joins = node.resolve()
            joins.extend(new_joins)
            return filters, joins

        return (
            self.create_sort(
                schema_field=self.schema.__fields__[self.name].type_,
                model_column=self.column,
                order=self.sort_["order"],
            ),
            [],
        )

    @property
    def name(self) -> str:
        """
        Return the name of the node or raise a BadRequest exception

        :return str: the name of the sort to sort on
        """
        name = self.sort_.get("field")

        if name is None:
            msg = "Can't find name of a sort"
            raise InvalidFilters(msg)

        if SPLIT_REL in name:
            name = name.split(SPLIT_REL)[0]

        if name not in self.schema.__fields__:
            msg = "{} has no attribute {}".format(self.schema.__name__, name)
            raise InvalidFilters(msg)

        return name

    @property
    def column(self) -> InstrumentedAttribute:
        """
        Get the column object.

        :return: the column to filter on
        """
        field = self.name

        model_field = get_model_field(self.schema, field)

        try:
            return getattr(self.model, model_field)
        except AttributeError:
            msg = "{} has no attribute {}".format(self.model.__name__, model_field)
            raise InvalidFilters(msg)

    @property
    def related_model(self) -> DeclarativeMeta:
        """
        Get the related model of a relationship field.

        :return: the related model.
        """
        relationship_field = self.name

        if relationship_field not in get_relationships(self.schema):
            msg = "{} has no relationship attribute {}".format(self.schema.__name__, relationship_field)
            raise InvalidFilters(msg)

        return get_related_model_cls(self.model, get_model_field(self.schema, relationship_field))

    @property
    def related_schema(self) -> Type[TypeSchema]:
        """
        Get the related schema of a relationship field.

        :return: the related schema
        """
        relationship_field = self.name

        if relationship_field not in get_relationships(self.schema):
            msg = "{} has no relationship attribute {}".format(self.schema.__name__, relationship_field)
            raise InvalidFilters(msg)

        return self.schema.__fields__[relationship_field].type_
