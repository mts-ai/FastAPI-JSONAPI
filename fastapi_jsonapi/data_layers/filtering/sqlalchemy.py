"""Helper to create sqlalchemy filters according to filter querystring parameter"""
import inspect
import logging
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    Union,
)

from pydantic import BaseConfig, BaseModel
from pydantic.fields import ModelField
from pydantic.validators import _VALIDATORS, find_validators
from sqlalchemy import and_, not_, or_
from sqlalchemy.orm import InstrumentedAttribute, aliased
from sqlalchemy.sql.elements import BinaryExpression

from fastapi_jsonapi.data_layers.shared import create_filters_or_sorts
from fastapi_jsonapi.data_typing import TypeModel, TypeSchema
from fastapi_jsonapi.exceptions import InvalidFilters, InvalidType
from fastapi_jsonapi.exceptions.json_api import HTTPException
from fastapi_jsonapi.schema import get_model_field, get_relationships
from fastapi_jsonapi.splitter import SPLIT_REL
from fastapi_jsonapi.utils.sqla import get_related_model_cls

log = logging.getLogger(__name__)

Filter = BinaryExpression
Join = List[Any]

FilterAndJoins = Tuple[
    Filter,
    List[Join],
]

# The mapping with validators using by to cast raw value to instance of target type
REGISTERED_PYDANTIC_TYPES: Dict[Type, List[Callable]] = dict(_VALIDATORS)

cast_failed = object()


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

    def _check_can_be_none(self, fields: list[ModelField]) -> bool:
        """
        Return True if None is possible value for target field
        """
        return any(field_item.allow_none for field_item in fields)

    def _cast_value_with_scheme(self, field_types: List[ModelField], value: Any) -> Tuple[Any, List[str]]:
        errors: List[str] = []
        casted_value = cast_failed

        for field_type in field_types:
            try:
                if isinstance(value, list):  # noqa: SIM108
                    casted_value = [field_type(item) for item in value]
                else:
                    casted_value = field_type(value)
            except (TypeError, ValueError) as ex:
                errors.append(str(ex))

        return casted_value, errors

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

        can_be_none = self._check_can_be_none(fields)

        if value is None:
            if can_be_none:
                return getattr(model_column, self.operator)(value)

            raise InvalidFilters(detail=f"The field `{schema_field.name}` can't be null")

        types = [i.type_ for i in fields]
        clear_value = None
        errors: List[str] = []

        pydantic_types, userspace_types = self._separate_types(types)

        if pydantic_types:
            func = self._cast_value_with_pydantic
            if isinstance(value, list):
                func = self._cast_iterable_with_pydantic
            clear_value, errors = func(pydantic_types, value, schema_field)

        if clear_value is None and userspace_types:
            log.warning("Filtering by user type values is not properly tested yet. Use this on your own risk.")

            clear_value, errors = self._cast_value_with_scheme(types, value)

            if clear_value is cast_failed:
                raise InvalidType(
                    detail=f"Can't cast filter value `{value}` to arbitrary type.",
                    errors=[HTTPException(status_code=InvalidType.status_code, detail=str(err)) for err in errors],
                )

        # Если None, при этом поле обязательное (среди типов в аннотации нет None, то кидаем ошибку)
        if clear_value is None and not can_be_none:
            raise InvalidType(
                detail=", ".join(errors),
                pointer=schema_field.name,
            )

        return getattr(model_column, self.operator)(clear_value)

    def _separate_types(self, types: List[Type]) -> Tuple[List[Type], List[Type]]:
        """
        Separates the types into two kinds.

        The first are those for which
        there are already validators defined by pydantic - str, int, datetime
        and some other built-in types.
        The second are all other types for which
        the `arbitrary_types_allowed` config is applied when defining the pydantic model
        """
        pydantic_types = [
            # skip format
            type_
            for type_ in types
            if type_ in REGISTERED_PYDANTIC_TYPES
        ]
        userspace_types = [
            # skip format
            type_
            for type_ in types
            if type_ not in REGISTERED_PYDANTIC_TYPES
        ]
        return pydantic_types, userspace_types

    def _validator_requires_model_field(self, validator: Callable) -> bool:
        """
        Check if validator accepts the `field` param

        :param validator:
        :return:
        """
        signature = inspect.signature(validator)
        parameters = signature.parameters

        if "field" not in parameters:
            return False

        field_param = parameters["field"]
        field_type = field_param.annotation

        return field_type == "ModelField" or field_type is ModelField

    def _cast_value_with_pydantic(
        self,
        types: List[Type],
        value: Any,
        schema_field: ModelField,
    ) -> Tuple[Optional[Any], List[str]]:
        result_value, errors = None, []

        for type_to_cast in types:
            for validator in find_validators(type_to_cast, BaseConfig):
                args = [value]
                # TODO: some other way to get all the validator's dependencies?
                if self._validator_requires_model_field(validator):
                    args.append(schema_field)
                try:
                    result_value = validator(*args)
                except Exception as ex:
                    errors.append(str(ex))
                else:
                    return result_value, errors

        return None, errors

    def _cast_iterable_with_pydantic(
        self,
        types: List[Type],
        values: List,
        schema_field: ModelField,
    ) -> Tuple[List, List[str]]:
        type_cast_failed = False
        failed_values = []

        result_values: List[Any] = []
        errors: List[str] = []

        for value in values:
            casted_value, cast_errors = self._cast_value_with_pydantic(
                types,
                value,
                schema_field,
            )
            errors.extend(cast_errors)

            if casted_value is None:
                type_cast_failed = True
                failed_values.append(value)

                continue

            result_values.append(casted_value)

        if type_cast_failed:
            msg = f"Can't parse items {failed_values} of value {values}"
            raise InvalidFilters(msg, pointer=schema_field.name)

        return result_values, errors

    def resolve(self) -> FilterAndJoins:  # noqa: PLR0911
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

        if SPLIT_REL in self.filter_.get("name", ""):
            value = {
                "name": SPLIT_REL.join(self.filter_["name"].split(SPLIT_REL)[1:]),
                "op": operator,
                "val": value,
            }
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

    def _create_filters(self, type_filter: str) -> FilterAndJoins:
        """
        Create or / and filters

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
