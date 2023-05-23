"""User Bio model."""
from typing import Dict, List

from sqlalchemy import JSON, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from examples.api_for_sqlalchemy.extensions.sqlalchemy import Base
from examples.api_for_sqlalchemy.utils.sqlalchemy.base_model_mixin import BaseModelMixin


class UserBio(Base, BaseModelMixin):
    __tablename__ = "user_bio"
    id = Column(Integer, primary_key=True, autoincrement=True)
    birth_city: str = Column(String, nullable=False, default="", server_default="")
    favourite_movies: str = Column(String, nullable=False, default="", server_default="")
    keys_to_ids_list: Dict[str, List[int]] = Column(JSON)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    user = relationship("User", back_populates="bio", uselist=False)

    def __repr__(self):
        return (
            f"{self.__class__.__name__}("
            f"id={self.id},"
            f" birth_city={self.birth_city!r},"
            f" favourite_movies={self.favourite_movies!r},"
            f" user_id={self.user_id}"
            ")"
        )
