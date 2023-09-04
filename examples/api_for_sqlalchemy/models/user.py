"""User model."""
from __future__ import annotations

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from examples.api_for_sqlalchemy.extensions.sqlalchemy import Base
from examples.api_for_sqlalchemy.models.enums import UserStatusEnum
from examples.api_for_sqlalchemy.utils.sqlalchemy.base_model_mixin import BaseModelMixin
from examples.api_for_sqlalchemy.utils.sqlalchemy.fields.enum import EnumColumn


class User(Base, BaseModelMixin):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    first_name: str = Column(String, nullable=True)
    last_name: str = Column(String, nullable=True)
    age: int = Column(Integer, nullable=True)
    status = Column(EnumColumn(UserStatusEnum), nullable=False, default=UserStatusEnum.active)
    email: str | None = Column(String, nullable=True)

    posts = relationship("Post", back_populates="user", uselist=True)
    bio = relationship("UserBio", back_populates="user", uselist=False)
    comments = relationship("PostComment", back_populates="author", uselist=True)
    computers = relationship("Computer", back_populates="user", uselist=True)

    def __repr__(self):
        return (
            f"{self.__class__.__name__}("
            f"id={self.id},"
            f" first_name={self.first_name!r},"
            f" last_name={self.last_name!r}"
            ")"
        )

    class Enum:
        Status = UserStatusEnum
