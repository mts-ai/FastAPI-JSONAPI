from typing import (
    TYPE_CHECKING,
    get_args,
)

# noinspection PyProtectedMember
from pydantic._internal._typing_extra import is_none_type

if TYPE_CHECKING:
    # noinspection PyProtectedMember
    from pydantic.fields import FieldInfo


def check_can_be_none(fields: list["FieldInfo"]) -> bool:
    """
    Return True if None is possible value for target field
    """
    for field in fields:
        if args := get_args(field.annotation):
            for arg in args:
                # None is probably only on the top level
                if is_none_type(arg):
                    return True
    return False
