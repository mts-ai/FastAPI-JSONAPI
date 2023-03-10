"""User model."""

from sqlalchemy import Column, Text, Integer

from examples.api_for_sqlalchemy.extensions.sqlalchemy import Base
from examples.api_for_sqlalchemy.models.enums import UserStatusEnum
from examples.api_for_sqlalchemy.utils.sqlalchemy.base_model_mixin import BaseModelMixin
from examples.api_for_sqlalchemy.utils.sqlalchemy.fields.enum import EnumColumn


class User(Base, BaseModelMixin):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    first_name: str = Column(Text, nullable=True)
    last_name: str = Column(Text, nullable=True)
    age: int = Column(Integer, nullable=True)
    status = Column(EnumColumn(UserStatusEnum), nullable=False, default=UserStatusEnum.active)

    def __repr__(self):
        rez = (
            f"<User "
            f"ID={self.tg_id} "
            f"name={self.first_name} {self.last_name} "
        )
        return rez + ">"

    class Enum:
        Status = UserStatusEnum
