"""
Splitter for filters, sorts and includes.

Previously used: '__'
"""

SPLIT_REL = "."


def prepare_field_name_for_filtering(field_name: str, type_op: str) -> str:
    """
    Prepare fields for use in ORM.

    :param field_name: name of the field by which the filtering will be performed.
    :param type_op: operation type.
    :return: prepared name field.
    """
    if type_op == "any":  # used to filter on to many relationships
        pass
    elif type_op == "between":  # used to filter a field between two values
        # between and given two values
        field_name = "{field_name}__range".format(field_name=field_name)
    elif type_op == "endswith":  # check if field ends with a string
        # if field ends with value
        field_name = "{field_name}__endswith".format(field_name=field_name)
    elif type_op == "iendswith":  # check if field ends with a string
        # if field ends with value (case insensitive)
        field_name = "{field_name}__iendswith".format(field_name=field_name)
    elif type_op == "eq":  # check if field is equal to something
        pass
    elif type_op == "ge":  # check if field is greater than or equal to something
        field_name = "{field_name}__gte".format(field_name=field_name)
    elif type_op == "gt":  # check if field is greater than to something
        field_name = "{field_name}__gt".format(field_name=field_name)
    elif type_op == "has":  # used to filter on to one relationships
        pass
    elif type_op == "in_":  # check if field is in a list of values
        field_name = "{field_name}__in".format(field_name=field_name)
    elif type_op == "is_":  # check if field is a value
        # field is null
        field_name = "{field_name}__isnull".format(field_name=field_name)
    elif type_op == "isnot":  # check if field is not a value
        # field is not null
        field_name = "{field_name}__not_isnull".format(field_name=field_name)
    elif type_op == "le":  # check if field is less than or equal to something
        field_name = "{field_name}__lte".format(field_name=field_name)
    elif type_op == "lt":  # check if field is less than to something
        field_name = "{field_name}__lt".format(field_name=field_name)
    elif type_op == "match":  # check if field match against a string or pattern
        pass
    elif type_op == "ne":  # check if field is not equal to something
        field_name = "{field_name}__not".format(field_name=field_name)
    elif type_op == "notilike":  # check if field does not contains a string (case insensitive)
        pass
    elif type_op == "notin_":  # check if field is not in a list of values
        field_name = "{field_name}__not_in".format(field_name=field_name)
    elif type_op == "notlike":  # check if field does not contains a string
        pass
    elif type_op == "startswith":  # check if field starts with a string
        # if field starts with value
        field_name = "{field_name}__startswith".format(field_name=field_name)
    elif type_op == "istartswith":  # check if field starts with a string
        # if field starts with value (case insensitive)
        field_name = "{field_name}__istartswith".format(field_name=field_name)
    elif type_op in {"contains", "like"}:  # field contains specified substring
        field_name = "{field_name}__contains".format(field_name=field_name)
    elif type_op in {"icontains", "ilike"}:  # case insensitive contains
        field_name = "{field_name}__icontains".format(field_name=field_name)
    elif type_op == "iequals":  # case insensitive equals
        field_name = "{field_name}__iexact".format(field_name=field_name)
    return field_name
