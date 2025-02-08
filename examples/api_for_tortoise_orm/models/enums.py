from enum import Enum


class UserStatusEnum(str, Enum):
    """
    Status user.
    """

    active = "active"
    archive = "archive"
    block = "block"
