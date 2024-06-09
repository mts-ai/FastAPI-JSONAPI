from fastapi_jsonapi.data_layers.fields.enum import Enum



class UserStatusEnum(str, Enum):  # noqa: SLOT000
    """
    Status user.
    """

    active = "active"
    archive = "archive"
    block = "block"
