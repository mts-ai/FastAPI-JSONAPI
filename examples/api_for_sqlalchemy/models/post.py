"""Post model."""

from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from examples.api_for_sqlalchemy.extensions.sqlalchemy import Base
from examples.api_for_sqlalchemy.utils.sqlalchemy.base_model_mixin import BaseModelMixin


class Post(Base, BaseModelMixin):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False, default="", server_default="")

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=False)
    user = relationship("User", back_populates="posts", uselist=False)

    comments = relationship("PostComment", back_populates="post", uselist=True)

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id} title={self.title!r} user_id={self.user_id})"
