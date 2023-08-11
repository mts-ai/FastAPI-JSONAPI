from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from examples.api_for_sqlalchemy.extensions.sqlalchemy import Base
from examples.api_for_sqlalchemy.utils.sqlalchemy.base_model_mixin import BaseModelMixin


class User(Base, BaseModelMixin):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name: str = Column(String)

    posts = relationship("Post", back_populates="user", uselist=True)
    bio = relationship("UserBio", back_populates="user", uselist=False)
    computers = relationship("Computer", back_populates="user", uselist=True)


class Computer(Base, BaseModelMixin):
    __tablename__ = "computers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user = relationship("User", back_populates="computers")


class UserBio(Base, BaseModelMixin):
    __tablename__ = "user_bio"
    id = Column(Integer, primary_key=True, autoincrement=True)
    birth_city: str = Column(String, nullable=False, default="", server_default="")
    favourite_movies: str = Column(String, nullable=False, default="", server_default="")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    user = relationship("User", back_populates="bio", uselist=False)
