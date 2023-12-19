"""
Previously used: '__'
"""
from typing import Protocol


def add_suffix(field_name: str, suffix: str, sep: str = "__") -> str:
    """
    joins str

    :param field_name:
    :param suffix:
    :param sep:
    :return:
    """
    return "".join((field_name, sep, suffix))


def type_op_any(field_name: str, type_op: str) -> str:
    """
    used to filter on to many relationships

    :param field_name:
    :param type_op:
    :return:
    """
    return field_name


def type_op_between(field_name: str, type_op: str) -> str:
    """
    used to filter a field between two values

    :param field_name:
    :param type_op:
    :return:
    """
    return add_suffix(field_name, "range")


def type_op_endswith(field_name: str, type_op: str) -> str:
    """
    check if field ends with a string

    :param field_name:
    :param type_op:
    :return:
    """
    return add_suffix(field_name, "endswith")


def type_op_iendswith(field_name: str, type_op: str) -> str:
    """
    check if field ends with a string

    :param field_name:
    :param type_op:
    :return:
    """
    return add_suffix(field_name, "iendswith")


def type_op_eq(field_name: str, type_op: str) -> str:
    """
    check if field is equal to something

    :param field_name:
    :param type_op:
    :return:
    """
    return field_name


def type_op_ge(field_name: str, type_op: str) -> str:
    """
    check if field is greater than or equal to something

    :param field_name:
    :param type_op:
    :return:
    """
    return add_suffix(field_name, "gte")


def type_op_gt(field_name: str, type_op: str) -> str:
    """
    check if field is greater than to something

    :param field_name:
    :param type_op:
    :return:
    """
    return add_suffix(field_name, "gt")


def type_op_has(field_name: str, type_op: str) -> str:
    """
    used to filter on to one relationship

    :param field_name:
    :param type_op:
    :return:
    """
    return field_name


def type_op_in_(field_name: str, type_op: str) -> str:
    """
    check if field is in a list of values

    :param field_name:
    :param type_op:
    :return:
    """
    return add_suffix(field_name, "in")


def type_op_is_(field_name: str, type_op: str) -> str:
    """
    check if field is null. wtf

    :param field_name:
    :param type_op:
    :return:
    """
    return add_suffix(field_name, "isnull")


def type_op_isnot(field_name: str, type_op: str) -> str:
    """
    check if field is not null. wtf

    :param field_name:
    :param type_op:
    :return:
    """
    return add_suffix(field_name, "not_isnull")


def type_op_le(field_name: str, type_op: str) -> str:
    """
    check if field is less than or equal to something

    :param field_name:
    :param type_op:
    :return:
    """
    return add_suffix(field_name, "lte")


def type_op_lt(field_name: str, type_op: str) -> str:
    """
    check if field is less than to something

    :param field_name:
    :param type_op:
    :return:
    """
    return add_suffix(field_name, "lt")


def type_op_match(field_name: str, type_op: str) -> str:
    """
    check if field match against a string or pattern

    :param field_name:
    :param type_op:
    :return:
    """
    return field_name


def type_op_ne(field_name: str, type_op: str) -> str:
    """
    check if field is not equal to something

    :param field_name:
    :param type_op:
    :return:
    """
    return add_suffix(field_name, "not")


def type_op_notilike(field_name: str, type_op: str) -> str:
    """
    check if field does not contains a string (case insensitive)

    :param field_name:
    :param type_op:
    :return:
    """
    return field_name


def type_op_notin_(field_name: str, type_op: str) -> str:
    """
    check if field is not in a list of values

    :param field_name:
    :param type_op:
    :return:
    """
    return add_suffix(field_name, "not_in")


def type_op_notlike(field_name: str, type_op: str) -> str:
    """
    check if field does not contains a string

    :param field_name:
    :param type_op:
    :return:
    """
    return field_name


def type_op_startswith(field_name: str, type_op: str) -> str:
    """
    check if field starts with value

    :param field_name:
    :param type_op:
    :return:
    """
    return add_suffix(field_name, "startswith")


def type_op_istartswith(field_name: str, type_op: str) -> str:
    """
    check if field starts with a string (case insensitive)

    :param field_name:
    :param type_op:
    :return:
    """
    return add_suffix(field_name, "istartswith")


def type_op_iequals(field_name: str, type_op: str) -> str:
    """
    case insensitive equals

    :param field_name:
    :param type_op:
    :return:
    """
    return add_suffix(field_name, "iexact")


def type_op_contains(field_name: str, type_op: str) -> str:
    """
    field contains specified substring

    :param field_name:
    :param type_op:
    :return:
    """
    return add_suffix(field_name, "contains")


def type_op_like(field_name: str, type_op: str) -> str:
    """
    field contains specified substring

    :param field_name:
    :param type_op:
    :return:
    """
    return add_suffix(field_name, "contains")


def type_op_icontains(field_name: str, type_op: str) -> str:
    """
    case insensitive contains

    :param field_name:
    :param type_op:
    :return:
    """
    return add_suffix(field_name, "icontains")


def type_op_ilike(field_name: str, type_op: str) -> str:
    """
    case insensitive contains

    :param field_name:
    :param type_op:
    :return:
    """
    return add_suffix(field_name, "icontains")


class ProcessTypeOperationFieldName(Protocol):
    def __call__(self, field_name: str, type_op: str) -> str:
        ...


filters_dict: dict[str, ProcessTypeOperationFieldName] = {
    "any": type_op_any,
    "between": type_op_between,
    "endswith": type_op_endswith,
    "iendswith": type_op_iendswith,
    "eq": type_op_eq,
    "ge": type_op_ge,
    "gt": type_op_gt,
    "has": type_op_has,
    "in_": type_op_in_,
    "is_": type_op_is_,
    "isnot": type_op_isnot,
    "le": type_op_le,
    "lt": type_op_lt,
    "match": type_op_match,
    "ne": type_op_ne,
    "notilike": type_op_notilike,
    "notin_": type_op_notin_,
    "notlike": type_op_notlike,
    "startswith": type_op_startswith,
    "istartswith": type_op_istartswith,
    "iequals": type_op_iequals,
    "contains": type_op_contains,
    "like": type_op_like,
    "icontains": type_op_icontains,
    "ilike": type_op_ilike,
}


def prepare_field_name_for_filtering(field_name: str, type_op: str) -> str:
    """
    Prepare fields for use in ORM.

    :param field_name: name of the field by which the filtering will be performed.
    :param type_op: operation type.
    :return: prepared name field.
    """
    func = filters_dict.get(type_op)
    if func:
        field_name = func(field_name=field_name, type_op=type_op)

    return field_name
