"""Post model."""
from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import (
    relationship,
    Mapped,
    mapped_column,
)

from examples.api_for_sqlalchemy.extensions.sqlalchemy import Base
from examples.api_for_sqlalchemy.utils.sqlalchemy.timestamps_mixin import TimestampsMixin

if TYPE_CHECKING:
    from .post_comment import PostComment
    from .user import User


class Post(Base, TimestampsMixin):
    __tablename__ = "posts"

    title: Mapped[str]
    body: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user: Mapped["User"] = relationship(back_populates="posts", uselist=False)

    comments: Mapped[list["PostComment"]] = relationship(
        "PostComment",
        back_populates="post",
        uselist=True,
    )

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id} title={self.title!r} user_id={self.user_id})"
