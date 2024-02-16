"""Helper to create sqlalchemy filters according to filter querystring parameter"""
import inspect
import logging
from collections.abc import Sequence
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    Union,
)

from pydantic import BaseConfig, BaseModel
from pydantic.fields import ModelField
from pydantic.validators import _VALIDATORS, find_validators
from sqlalchemy import and_, false, not_, or_
from sqlalchemy.orm import aliased
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.orm.util import AliasedClass
from sqlalchemy.sql.elements import BinaryExpression, BooleanClauseList

from fastapi_jsonapi.data_typing import TypeModel, TypeSchema
from fastapi_jsonapi.exceptions import InvalidFilters, InvalidType
from fastapi_jsonapi.exceptions.json_api import HTTPException
from fastapi_jsonapi.schema import JSONAPISchemaIntrospectionError, get_model_field, get_relationships

log = logging.getLogger(__name__)

RELATIONSHIP_SPLITTER = "."

# The mapping with validators using by to cast raw value to instance of target type
REGISTERED_PYDANTIC_TYPES: Dict[Type, List[Callable]] = dict(_VALIDATORS)

cast_failed = object()

RelationshipPath = str


class RelationshipFilteringInfo(BaseModel):
    target_schema: Type[TypeSchema]
    model: Type[TypeModel]
    aliased_model: AliasedClass
    join_column: InstrumentedAttribute

    class Config:
        arbitrary_types_allowed = True


def check_can_be_none(fields: list[ModelField]) -> bool:
    """
    Return True if None is possible value for target field
    """
    return any(field_item.allow_none for field_item in fields)


def separate_types(types: List[Type]) -> Tuple[List[Type], List[Type]]:
    """
    Separates the types into two kinds.

    The first are those for which there are already validators
    defined by pydantic - str, int, datetime and some other built-in types.
    The second are all other types for which the `arbitrary_types_allowed`
    config is applied when defining the pydantic model
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


def validator_requires_model_field(validator: Callable) -> bool:
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


def cast_value_with_pydantic(
    types: List[Type],
    value: Any,
    schema_field: ModelField,
) -> Tuple[Optional[Any], List[str]]:
    result_value, errors = None, []

    for type_to_cast in types:
        for validator in find_validators(type_to_cast, BaseConfig):
            args = [value]
            # TODO: some other way to get all the validator's dependencies?
            if validator_requires_model_field(validator):
                args.append(schema_field)
            try:
                result_value = validator(*args)
            except Exception as ex:
                errors.append(str(ex))
            else:
                return result_value, errors

    return None, errors


def cast_iterable_with_pydantic(
    types: List[Type],
    values: List,
    schema_field: ModelField,
) -> Tuple[List, List[str]]:
    type_cast_failed = False
    failed_values = []

    result_values: List[Any] = []
    errors: List[str] = []

    for value in values:
        casted_value, cast_errors = cast_value_with_pydantic(
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


def cast_value_with_scheme(field_types: List[Type], value: Any) -> Tuple[Any, List[str]]:
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
        else:
            return casted_value, errors

    return casted_value, errors


def build_filter_expression(
    schema_field: ModelField,
    model_column: InstrumentedAttribute,
    operator: str,
    value: Any,
) -> BinaryExpression:
    """
    Builds sqlalchemy filter expression, like YourModel.some_field == value

    Custom sqlalchemy filtering logic can be created in a schemas field for any operator
    To implement a new filtering logic (override existing or create a new one)
    create a method inside a field following this pattern:  `_<your_op_name>_sql_filter_`

    :param schema_field: schemas field instance
    :param model_column: sqlalchemy column instance
    :param operator: your operator, for example: "eq", "in", "ilike_str_array", ...
    :param value: filtering value

    """
    fields = [schema_field]

    # for Union annotations
    if schema_field.sub_fields:
        fields = list(schema_field.sub_fields)

    can_be_none = check_can_be_none(fields)

    if value is None:
        if can_be_none:
            return getattr(model_column, operator)(value)

        raise InvalidFilters(detail=f"The field `{schema_field.name}` can't be null")

    types = [i.type_ for i in fields]
    casted_value = None
    errors: List[str] = []

    pydantic_types, userspace_types = separate_types(types)

    if pydantic_types:
        func = cast_value_with_pydantic
        if isinstance(value, list):
            func = cast_iterable_with_pydantic
        casted_value, errors = func(pydantic_types, value, schema_field)

    if casted_value is None and userspace_types:
        log.warning("Filtering by user type values is not properly tested yet. Use this on your own risk.")

        casted_value, errors = cast_value_with_scheme(types, value)

        if casted_value is cast_failed:
            raise InvalidType(
                detail=f"Can't cast filter value `{value}` to arbitrary type.",
                errors=[HTTPException(status_code=InvalidType.status_code, detail=str(err)) for err in errors],
            )

    if casted_value is None and not can_be_none:
        raise InvalidType(
            detail=", ".join(errors),
            pointer=schema_field.name,
        )

    return getattr(model_column, operator)(casted_value)


def is_terminal_node(filter_item: dict) -> bool:
    """
    If node shape is:

    {
        "name: ...,
        "op: ...,
        "val: ...,
    }
    """
    terminal_node_keys = {"name", "op", "val"}
    return set(filter_item.keys()) == terminal_node_keys


def is_relationship_filter(name: str) -> bool:
    return RELATIONSHIP_SPLITTER in name


def gather_relationship_paths(filter_item: Union[dict, list]) -> Set[str]:
    """
    Extracts relationship paths from query filter
    """
    names = set()

    if isinstance(filter_item, list):
        for sub_item in filter_item:
            names.update(gather_relationship_paths(sub_item))

    elif is_terminal_node(filter_item):
        name = filter_item["name"]

        if RELATIONSHIP_SPLITTER not in name:
            return set()

        return {RELATIONSHIP_SPLITTER.join(name.split(RELATIONSHIP_SPLITTER)[:-1])}

    else:
        for sub_item in filter_item.values():
            names.update(gather_relationship_paths(sub_item))

    return names


def get_model_column(
    model: Type[TypeModel],
    schema: Type[TypeSchema],
    field_name: str,
) -> InstrumentedAttribute:
    try:
        model_field = get_model_field(schema, field_name)
    except JSONAPISchemaIntrospectionError as e:
        raise InvalidFilters(str(e))

    try:
        return getattr(model, model_field)
    except AttributeError:
        msg = "{} has no attribute {}".format(model.__name__, model_field)
        raise InvalidFilters(msg)


def get_operator(model_column: InstrumentedAttribute, operator_name: str) -> str:
    """
    Get the function operator from his name

    :return callable: a callable to make operation on a column
    """
    operators = (
        f"__{operator_name}__",
        f"{operator_name}_",
        operator_name,
    )

    for op in operators:
        if hasattr(model_column, op):
            return op

    msg = "{} has no operator {}".format(model_column.key, operator_name)
    raise InvalidFilters(msg)


def get_custom_filter_expression_callable(schema_field, operator: str) -> Callable:
    return schema_field.field_info.extra.get(
        f"_{operator}_sql_filter_",
    )


def gather_relationships_info(
    model: Type[TypeModel],
    schema: Type[TypeSchema],
    relationship_path: List[str],
    collected_info: dict[RelationshipPath, RelationshipFilteringInfo],
    target_relationship_idx: int = 0,
    prev_aliased_model: Optional[Any] = None,
) -> dict[RelationshipPath, RelationshipFilteringInfo]:
    is_last_relationship = target_relationship_idx == len(relationship_path) - 1
    target_relationship_path = RELATIONSHIP_SPLITTER.join(
        relationship_path[: target_relationship_idx + 1],
    )
    target_relationship_name = relationship_path[target_relationship_idx]

    if target_relationship_name not in set(get_relationships(schema)):
        msg = f"There are no relationship '{target_relationship_name}' defined in schema {schema.__name__}"
        raise InvalidFilters(msg)

    target_schema = schema.__fields__[target_relationship_name].type_
    target_model = getattr(model, target_relationship_name).property.mapper.class_

    if prev_aliased_model:
        join_column = get_model_column(
            model=prev_aliased_model,
            schema=schema,
            field_name=target_relationship_name,
        )
    else:
        join_column = get_model_column(
            model,
            schema,
            target_relationship_name,
        )

    aliased_model = aliased(target_model)
    collected_info[target_relationship_path] = RelationshipFilteringInfo(
        target_schema=target_schema,
        model=target_model,
        aliased_model=aliased_model,
        join_column=join_column,
    )

    if not is_last_relationship:
        return gather_relationships_info(
            model=target_model,
            schema=target_schema,
            relationship_path=relationship_path,
            collected_info=collected_info,
            target_relationship_idx=target_relationship_idx + 1,
            prev_aliased_model=aliased_model,
        )

    return collected_info


def gather_relationships(
    entrypoint_model: Type[TypeModel],
    schema: Type[TypeSchema],
    relationship_paths: Set[str],
) -> dict[RelationshipPath, RelationshipFilteringInfo]:
    collected_info = {}
    for relationship_path in sorted(relationship_paths):
        gather_relationships_info(
            model=entrypoint_model,
            schema=schema,
            relationship_path=relationship_path.split(RELATIONSHIP_SPLITTER),
            collected_info=collected_info,
        )

    return collected_info


def prepare_relationships_info(
    model: Type[TypeModel],
    schema: Type[TypeSchema],
    filter_info: list,
):
    # TODO: do this on application startup or use the cache
    relationship_paths = gather_relationship_paths(filter_info)
    return gather_relationships(
        entrypoint_model=model,
        schema=schema,
        relationship_paths=relationship_paths,
    )


def build_terminal_node_filter_expressions(
    filter_item: Dict,
    target_schema: Type[TypeSchema],
    target_model: Type[TypeModel],
    relationships_info: Dict[RelationshipPath, RelationshipFilteringInfo],
):
    name: str = filter_item["name"]
    if is_relationship_filter(name):
        *relationship_path, field_name = name.split(RELATIONSHIP_SPLITTER)
        relationship_info: RelationshipFilteringInfo = relationships_info[
            RELATIONSHIP_SPLITTER.join(relationship_path)
        ]
        model_column = get_model_column(
            model=relationship_info.aliased_model,
            schema=relationship_info.target_schema,
            field_name=field_name,
        )
        target_schema = relationship_info.target_schema
    else:
        field_name = name
        model_column = get_model_column(
            model=target_model,
            schema=target_schema,
            field_name=field_name,
        )

    schema_field = target_schema.__fields__[field_name]

    filter_operator = filter_item["op"]
    custom_filter_expression: Callable = get_custom_filter_expression_callable(
        schema_field=schema_field,
        operator=filter_operator,
    )
    if custom_filter_expression is None:
        return build_filter_expression(
            schema_field=schema_field,
            model_column=model_column,
            operator=get_operator(
                model_column=model_column,
                operator_name=filter_operator,
            ),
            value=filter_item["val"],
        )

    custom_call_result = custom_filter_expression(
        schema_field=schema_field,
        model_column=model_column,
        value=filter_item["val"],
        operator=filter_operator,
    )
    if isinstance(custom_call_result, Sequence):
        expected_len = 2
        if len(custom_call_result) != expected_len:
            log.error(
                "Invalid filter, returned sequence length is not %s: %s, len=%s",
                expected_len,
                custom_call_result,
                len(custom_call_result),
            )
            raise InvalidFilters(detail="Custom sql filter backend error.")
        log.warning(
            "Custom filter result of `[expr, [joins]]` is deprecated."
            " Please return only filter expression from now on. "
            "(triggered on schema field %s for filter operator %s on column %s)",
            schema_field,
            filter_operator,
            model_column,
        )
        custom_call_result = custom_call_result[0]
    return custom_call_result


def build_filter_expressions(
    filter_item: Dict,
    target_schema: Type[TypeSchema],
    target_model: Type[TypeModel],
    relationships_info: Dict[RelationshipPath, RelationshipFilteringInfo],
) -> Union[BinaryExpression, BooleanClauseList]:
    """
    Return sqla expressions.

    Builds sqlalchemy expression which can be use
    in where condition: query(Model).where(build_filter_expressions(...))
    """
    if is_terminal_node(filter_item):
        return build_terminal_node_filter_expressions(
            filter_item=filter_item,
            target_schema=target_schema,
            target_model=target_model,
            relationships_info=relationships_info,
        )

    if not isinstance(filter_item, dict):
        log.warning("Could not build filtering expressions %s", locals())
        # dirty. refactor.
        return not_(false())

    sqla_logic_operators = {
        "or": or_,
        "and": and_,
        "not": not_,
    }

    if len(logic_operators := set(filter_item.keys())) > 1:
        msg = (
            f"In each logic node expected one of operators: {set(sqla_logic_operators.keys())} "
            f"but got {len(logic_operators)}: {logic_operators}"
        )
        raise InvalidFilters(msg)

    if (logic_operator := logic_operators.pop()) not in set(sqla_logic_operators.keys()):
        msg = f"Not found logic operator {logic_operator} expected one of {set(sqla_logic_operators.keys())}"
        raise InvalidFilters(msg)

    op = sqla_logic_operators[logic_operator]

    if logic_operator == "not":
        return op(
            build_filter_expressions(
                filter_item=filter_item[logic_operator],
                target_schema=target_schema,
                target_model=target_model,
                relationships_info=relationships_info,
            ),
        )

    expressions = []
    for filter_sub_item in filter_item[logic_operator]:
        expressions.append(
            build_filter_expressions(
                filter_item=filter_sub_item,
                target_schema=target_schema,
                target_model=target_model,
                relationships_info=relationships_info,
            ),
        )

    return op(*expressions)


def create_filters_and_joins(
    filter_info: list,
    model: Type[TypeModel],
    schema: Type[TypeSchema],
):
    relationships_info = prepare_relationships_info(
        model=model,
        schema=schema,
        filter_info=filter_info,
    )
    expressions = build_filter_expressions(
        filter_item={"and": filter_info},
        target_model=model,
        target_schema=schema,
        relationships_info=relationships_info,
    )
    joins = [(info.aliased_model, info.join_column) for info in relationships_info.values()]
    return expressions, joins
