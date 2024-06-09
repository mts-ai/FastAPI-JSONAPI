"""User model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Column
from sqlalchemy.orm import (
    Mapped,
    relationship,
)

from examples.api_for_sqlalchemy.extensions.sqlalchemy import Base
from examples.api_for_sqlalchemy.models.enums import UserStatusEnum
from examples.api_for_sqlalchemy.utils.sqlalchemy.fields.enum import EnumColumn
from examples.api_for_sqlalchemy.utils.sqlalchemy.timestamps_mixin import TimestampsMixin

if TYPE_CHECKING:
    from .computer import Computer
    from .post import Post
    from .post_comment import PostComment
    from .user_bio import UserBio


class User(Base, TimestampsMixin):
    __tablename__ = "users"

    first_name: Mapped[str | None]
    last_name: Mapped[str | None]
    age: Mapped[int | None]
    # ? оно нам надо?
    status = Column(EnumColumn(UserStatusEnum), nullable=False, default=UserStatusEnum.active)
    email: Mapped[str | None]

    posts: Mapped[list[Post]] = relationship("Post", back_populates="user", uselist=True)
    bio: Mapped[UserBio] = relationship("UserBio", back_populates="user", uselist=False)
    comments: Mapped[list[PostComment]] = relationship("PostComment", back_populates="author", uselist=True)
    computers: Mapped[list[Computer]] = relationship("Computer", back_populates="user", uselist=True)

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
