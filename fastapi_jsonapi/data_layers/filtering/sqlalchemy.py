"""Helper to create sqlalchemy filters according to filter querystring parameter"""
from typing import Any, List, Optional, Tuple, Type, Union

from pydantic import BaseModel
from pydantic.fields import ModelField
from sqlalchemy import and_, not_, or_
from sqlalchemy.orm import InstrumentedAttribute, aliased
from sqlalchemy.sql.elements import BinaryExpression
from sqlalchemy.sql.schema import Column
from sqlalchemy.sql.sqltypes import JSON

from fastapi_jsonapi.data_layers.shared import create_filters_or_sorts
from fastapi_jsonapi.data_typing import TypeModel, TypeSchema
from fastapi_jsonapi.exceptions import InvalidFilters, InvalidType
from fastapi_jsonapi.schema import get_model_field, get_relationships
from fastapi_jsonapi.splitter import SPLIT_REL
from fastapi_jsonapi.utils.sqla import get_related_model_cls

Filter = BinaryExpression
Join = List[Any]

FilterAndJoins = Tuple[
    Filter,
    List[Join],
]


def create_filters(model: Type[TypeModel], filter_info: Union[list, dict], schema: Type[TypeSchema]):
    """
    Apply filters from filters information to base query
    :param model: the model of the node
    :param filter_info: current node filter information
    :param schema: the resource
    """
    return create_filters_or_sorts(model, filter_info, Node, schema)


class Node:
    """Helper to recursively create filters with sqlalchemy according to filter querystring parameter"""

    def __init__(self, model: Type[TypeModel], filter_: dict, schema: Type[TypeSchema]) -> None:
        """
        Initialize an instance of a filter node

        :param model: an sqlalchemy model
        :param dict filter_: filters information of the current node and deeper nodes
        :param schema: the serializer
        """
        self.model = model
        self.filter_ = filter_
        self.schema = schema

    def create_filter(self, schema_field: ModelField, model_column, operator, value):
        """
        Create sqlalchemy filter
        :param schema_field:
        :param model_column: column sqlalchemy
        :param operator:
        :param value:
        :return:
        """
        """
        Custom sqlachemy filtering logic can be created in a schemas field for any operator
        To implement a new filtering logic (override existing or create a new one)
        create a method inside a field following this pattern:
        `_<your_op_name>_sql_filter_`. Each filtering method has to accept these params:
        * schema_field - schemas field instance
        * model_column - sqlalchemy column instance
        * value - filtering value
        * operator - your operator, for example: "eq", "in", "ilike_str_array", ...
        """
        # Here we have to deserialize and validate fields, that are used in filtering,
        # so the Enum fields are loaded correctly

        if schema_field.sub_fields:  # noqa: SIM108
            # Для случаев когда в схеме тип Union
            fields = list(schema_field.sub_fields)
        else:
            fields = [schema_field]
        types = [i.type_ for i in fields]
        clear_value = None
        errors: List[str] = []
        for i_type in types:
            try:
                if isinstance(value, list):  # noqa: SIM108
                    clear_value = [i_type(item) for item in value]
                else:
                    clear_value = i_type(value)
            except (TypeError, ValueError) as ex:
                errors.append(str(ex))
        # Если None, при этом поле обязательное (среди типов в аннотации нет None, то кидаем ошибку)
        if clear_value is None and not any(not i_f.required for i_f in fields):
            raise InvalidType(detail=", ".join(errors))
        return getattr(model_column, self.operator)(clear_value)

    def _is_json_column(self, column_name: str) -> bool:
        column: Optional[Column] = self.model.__table__.columns.get(column_name)

        if column is None:
            return False

        return isinstance(column.type, JSON)

    # TODO: refactor and remove ignore PLR0911, PLR0912
    def resolve(self) -> FilterAndJoins:  # noqa: PLR0911, PLR0912
        """Create filter for a particular node of the filter tree"""
        if "or" in self.filter_:
            return self._create_filters(type_filter="or")
        if "and" in self.filter_:
            return self._create_filters(type_filter="and")
        if "not" in self.filter_:
            filter_, joins = Node(self.model, self.filter_["not"], self.schema).resolve()
            return not_(filter_), joins

        value = self.value
        operator = self.filter_["op"]
        schema_field: ModelField = self.schema.__fields__[self.name]

        custom_filter = schema_field.field_info.extra.get(f"_{operator}_sql_filter_")
        if custom_filter:
            return custom_filter(
                schema_field=schema_field,
                model_column=self.column,
                value=value,
                operator=operator,
            )

        # TODO: check if relationship or inner schema
        # TODO: create base schema `BaseJsonModel(BaseModel)`? reuse:
        #  https://github.com/AdCombo/combojsonapi/blob/45a43cf28c6496195c6e6762955db16f9a813b2f/combojsonapi/postgresql_jsonb/plugin.py#L103-L120

        if SPLIT_REL in self.filter_.get("name", ""):
            current_rel_or_column_name, *rel_names = self.filter_["name"].split(SPLIT_REL)
            value = {
                "name": SPLIT_REL.join(rel_names),
                "op": operator,
                "val": value,
            }

            is_json_filter = self._is_json_column(current_rel_or_column_name)
            if is_json_filter:
                return self._json_inner_filtering(value)

            return self._relationship_filtering(value)

        if isinstance(value, dict):
            return self._relationship_filtering(value)

        if schema_field.sub_fields:  # noqa: SIM108
            # Для случаев когда в схеме тип Union
            types = [i.type_ for i in schema_field.sub_fields]
        else:
            types = [schema_field.type_]
        for i_type in types:
            try:
                if issubclass(i_type, BaseModel):
                    value = {
                        "name": self.name,
                        "op": operator,
                        "val": value,
                    }
                    return self._relationship_filtering(value)
            except (TypeError, ValueError):
                pass

        return (
            self.create_filter(
                schema_field=schema_field,
                model_column=self.column,
                operator=operator,
                value=value,
            ),
            [],
        )

    def _relationship_filtering(self, value):
        alias = aliased(self.related_model)
        joins = [[alias, self.column]]
        node = Node(alias, value, self.related_schema)
        filters, new_joins = node.resolve()
        joins.extend(new_joins)
        return filters, joins

    def _json_inner_filtering(self, value):
        # TODO!! Upgrade Node usage :thinking:
        node = Node(self.related_model, value, self.related_schema)
        filters, new_joins = node.resolve()
        # joins.extend(new_joins)
        return filters, []

    def _create_filters(self, type_filter: str) -> FilterAndJoins:
        """
        Создаём  фильтр or или and
        :param type_filter: 'or' или 'and'
        :return:
        """
        nodes = [Node(self.model, filter_, self.schema).resolve() for filter_ in self.filter_[type_filter]]
        joins = []
        for i_node in nodes:
            joins.extend(i_node[1])
        op = and_ if type_filter == "and" else or_
        return op(*[i_node[0] for i_node in nodes]), joins

    @property
    def name(self) -> str:
        """
        Return the name of the node or raise a BadRequest exception

        :return str: the name of the field to filter on
        """
        name = self.filter_.get("name")

        if name is None:
            msg = "Can't find name of a filter"
            raise InvalidFilters(msg)

        if SPLIT_REL in name:
            name = name.split(SPLIT_REL)[0]

        if name not in self.schema.__fields__:
            msg = "{} has no attribute {}".format(self.schema.__name__, name)
            raise InvalidFilters(msg)

        return name

    @property
    def op(self) -> str:
        """
        Return the operator of the node

        :return str: the operator to use in the filter
        """
        try:
            return self.filter_["op"]
        except KeyError:
            msg = "Can't find op of a filter"
            raise InvalidFilters(msg)

    @property
    def column(self) -> InstrumentedAttribute:
        """Get the column object"""
        field = self.name

        model_field = get_model_field(self.schema, field)

        is_json_field = hasattr(self.model, "type") and isinstance(self.model.type, JSON)
        if is_json_field:
            return self.model.op("->>")(model_field)

        try:
            return getattr(self.model, model_field)
        except AttributeError:
            msg = "{} has no attribute {}".format(self.model.__name__, model_field)
            raise InvalidFilters(msg)

    @property
    def operator(self) -> name:
        """
        Get the function operator from his name

        :return callable: a callable to make operation on a column
        """
        operators = (self.op, self.op + "_", "__" + self.op + "__")

        for op in operators:
            if hasattr(self.column, op):
                return op

        msg = "{} has no operator {}".format(self.column.key, self.op)
        raise InvalidFilters(msg)

    @property
    def value(self) -> Union[dict, list, int, str, float]:
        """
        Get the value to filter on

        :return: the value to filter on
        """
        if self.filter_.get("field") is not None:
            try:
                result = getattr(self.model, self.filter_["field"])
            except AttributeError:
                msg = "{} has no attribute {}".format(self.model.__name__, self.filter_["field"])
                raise InvalidFilters(msg)
            else:
                return result
        else:
            if "val" not in self.filter_:
                msg = "Can't find value or field in a filter"
                raise InvalidFilters(msg)

            return self.filter_["val"]

    @property
    def related_model(self):
        """
        Get the related model of a relationship field

        :return DeclarativeMeta: the related model
        """
        relationship_field = self.name

        if relationship_field not in get_relationships(self.schema):
            msg = "{} has no relationship attribute {}".format(self.schema.__name__, relationship_field)
            raise InvalidFilters(msg)

        return get_related_model_cls(self.model, get_model_field(self.schema, relationship_field))

    @property
    def related_schema(self):
        """
        Get the related schema of a relationship field

        :return Schema: the related schema
        """
        relationship_field = self.name

        if relationship_field not in get_relationships(self.schema):
            msg = "{} has no relationship attribute {}".format(self.schema.__name__, relationship_field)
            raise InvalidFilters(msg)

        return self.schema.__fields__[relationship_field].type_
