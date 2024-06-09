"""Post Comment model."""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from examples.api_for_sqlalchemy.extensions.sqlalchemy import Base
from examples.api_for_sqlalchemy.utils.sqlalchemy.timestamps_mixin import TimestampsMixin

if TYPE_CHECKING:
    from .post import Post
    from .user import User


class PostComment(Base, TimestampsMixin):
    __tablename__ = "post_comments"

    text: Mapped[str] = mapped_column(String, nullable=False, default="", server_default="")

    post_id: Mapped[int] = mapped_column(Integer, ForeignKey("posts.id"), nullable=False, unique=False)
    post: Mapped["Post"] = relationship(back_populates="comments", uselist=False)

    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, unique=False)
    author: Mapped["User"] = relationship(back_populates="comments", uselist=False)

    def __repr__(self):
        return (
            f"{self.__class__.__name__}("
            f"id={self.id},"
            f" text={self.text!r},"
            f" author_id={self.author_id},"
            f" post_id={self.post_id}"
            ")"
        )
