"""Post Comment model."""

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from examples.api_for_sqlalchemy.extensions.sqlalchemy import Base
from examples.api_for_sqlalchemy.utils.sqlalchemy.base_model_mixin import BaseModelMixin


class PostComment(Base, BaseModelMixin):
    __tablename__ = "post_comments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    text: str = Column(String, nullable=False, default="", server_default="")

    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False, unique=False)
    post = relationship("Post", back_populates="comments", uselist=False)

    author_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=False)
    author = relationship("User", back_populates="comments", uselist=False)

    def __repr__(self):
        return (
            f"{self.__class__.__name__}("
            f"id={self.id},"
            f" text={self.text!r},"
            f" author_id={self.author_id},"
            f" post_id={self.post_id}"
            ")"
        )
