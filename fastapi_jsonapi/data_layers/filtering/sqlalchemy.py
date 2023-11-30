"""Helper to create sqlalchemy filters according to filter querystring parameter"""
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Set,
    Type,
    Union,
)

from pydantic import BaseModel
from pydantic.fields import ModelField
from sqlalchemy import and_, not_, or_
from sqlalchemy.orm import aliased
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.orm.util import AliasedClass
from sqlalchemy.sql.elements import BinaryExpression, BooleanClauseList

from fastapi_jsonapi.data_typing import TypeModel, TypeSchema
from fastapi_jsonapi.exceptions import InvalidFilters, InvalidType
from fastapi_jsonapi.schema import get_model_field, get_relationships

RELATIONSHIP_SPLITTER = "."

RelationshipPath = str


class RelationshipInfo(BaseModel):
    target_schema: Type[TypeSchema]
    model: Type[TypeModel]
    aliased_model: AliasedClass
    column: InstrumentedAttribute

    class Config:
        arbitrary_types_allowed = True


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

    casted_value = None
    errors: List[str] = []

    for cast_type in [field.type_ for field in fields]:
        try:
            casted_value = [cast_type(item) for item in value] if isinstance(value, list) else cast_type(value)
        except (TypeError, ValueError) as ex:
            errors.append(str(ex))

    all_fields_required = all(field.required for field in fields)

    if casted_value is None and all_fields_required:
        raise InvalidType(detail=", ".join(errors))

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


def gather_relationship_paths(filter_item: Union[List, Dict]) -> Set[str]:
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
    model_field = get_model_field(schema, field_name)

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
    collected_info: dict,
    target_relationship_idx: int = 0,
) -> dict[RelationshipPath, RelationshipInfo]:
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
    target_column = get_model_column(
        model,
        schema,
        target_relationship_name,
    )
    collected_info[target_relationship_path] = RelationshipInfo(
        target_schema=target_schema,
        model=target_model,
        aliased_model=aliased(target_model),
        column=target_column,
    )

    if not is_last_relationship:
        return gather_relationships_info(
            target_model,
            target_schema,
            relationship_path,
            collected_info,
            target_relationship_idx + 1,
        )

    return collected_info


def gather_relationships(
    entrypoint_model: Type[TypeModel],
    schema: Type[TypeSchema],
    relationship_paths: Set[str],
) -> dict[RelationshipPath, RelationshipInfo]:
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


def build_filter_expressions(
    filter_item: Union[dict, list],
    target_schema: Type[TypeSchema],
    target_model: Type[TypeModel],
    relationships_info: dict[RelationshipPath, RelationshipInfo],
) -> Union[BinaryExpression, BooleanClauseList]:
    """
    Builds sqlalchemy expression which can be use
    in where condition: query(Model).where(build_filter_expressions(...))
    """
    if is_terminal_node(filter_item):
        name = filter_item["name"]
        target_schema = target_schema

        if is_relationship_filter(name):
            *relationship_path, field_name = name.split(RELATIONSHIP_SPLITTER)
            relationship_info: RelationshipInfo = relationships_info[RELATIONSHIP_SPLITTER.join(relationship_path)]
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

        custom_filter_expression = get_custom_filter_expression_callable(
            schema_field=schema_field,
            operator=filter_item["op"],
        )
        if custom_filter_expression:
            return custom_filter_expression(
                schema_field=schema_field,
                model_column=model_column,
                value=filter_item["val"],
                operator=filter_item["op"],
            )
        else:
            return build_filter_expression(
                schema_field=schema_field,
                model_column=model_column,
                operator=get_operator(
                    model_column=model_column,
                    operator_name=filter_item["op"],
                ),
                value=filter_item["val"],
            )

    if isinstance(filter_item, dict):
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
    joins = [(info.aliased_model, info.column) for info in relationships_info.values()]
    return expressions, joins
