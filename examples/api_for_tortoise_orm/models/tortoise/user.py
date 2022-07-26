"""User model."""


from tortoise import (
    fields,
    models,
)

from examples.api_for_tortoise_orm.models.enums import UserStatusEnum

MAX_LEN_NAME = 100
NOMENCLATURE_NUMBER_FIELD_LENGTH = 100


class User(models.Model):
    """The user model."""

    class Enum:
        status = UserStatusEnum

    id: int = fields.IntField(pk=True)
    first_name: str = fields.CharField(max_length=MAX_LEN_NAME)
    last_name: str = fields.CharField(max_length=MAX_LEN_NAME)
    status: UserStatusEnum = fields.CharEnumField(UserStatusEnum)
    created_at = fields.DatetimeField(null=True, auto_now_add=True)
    modified_at = fields.DatetimeField(null=True, auto_now=True)

    class Meta:
        table = "users"
