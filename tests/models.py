from typing import Dict, List, Optional

from sqlalchemy import JSON, Column, ForeignKey, Index, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import declared_attr, relationship


class Base:
    @declared_attr
    def __tablename__(cls):
        """
        Generate table name
        :return:
        """
        return f"{cls.__name__.lower()}s"


class AutoIdMixin:
    @declared_attr
    def id(cls):
        return Column(Integer, primary_key=True, autoincrement=True)


Base = declarative_base(cls=Base)


class User(AutoIdMixin, Base):
    name: str = Column(String, nullable=False, unique=True)
    age: int = Column(Integer, nullable=True)
    email: Optional[str] = Column(String, nullable=True)

    posts = relationship("Post", back_populates="user", uselist=True)
    bio = relationship(
        "UserBio",
        back_populates="user",
        uselist=False,
        cascade="save-update, merge, delete, delete-orphan",
    )
    comments = relationship(
        "PostComment",
        back_populates="author",
        uselist=True,
        cascade="save-update, merge, delete, delete-orphan",
    )

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id}, name={self.name!r})"


class UserBio(AutoIdMixin, Base):
    birth_city: str = Column(String, nullable=False, default="", server_default="")
    favourite_movies: str = Column(String, nullable=False, default="", server_default="")
    keys_to_ids_list: Dict[str, List[int]] = Column(JSON)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    user = relationship(
        "User",
        back_populates="bio",
        uselist=False,
    )

    def __repr__(self):
        return (
            f"{self.__class__.__name__}("
            f"id={self.id},"
            f" birth_city={self.birth_city!r},"
            f" favourite_movies={self.favourite_movies!r},"
            f" user_id={self.user_id}"
            ")"
        )


class Post(AutoIdMixin, Base):
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False, default="", server_default="")

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=False)
    user = relationship(
        "User",
        back_populates="posts",
        uselist=False,
    )

    comments = relationship(
        "PostComment",
        back_populates="post",
        uselist=True,
        cascade="save-update, merge, delete, delete-orphan",
    )

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id} title={self.title!r} user_id={self.user_id})"


class PostComment(AutoIdMixin, Base):
    text: str = Column(String, nullable=False, default="", server_default="")

    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False, unique=False)
    post = relationship(
        "Post",
        back_populates="comments",
        uselist=False,
    )

    author_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=False)
    author = relationship(
        "User",
        back_populates="comments",
        uselist=False,
    )

    def __repr__(self):
        return (
            f"{self.__class__.__name__}("
            f"id={self.id},"
            f" text={self.text!r},"
            f" author_id={self.author_id},"
            f" post_id={self.post_id}"
            ")"
        )


class Parent(AutoIdMixin, Base):
    __tablename__ = "left_table_parents"
    name = Column(String, nullable=False)
    children = relationship(
        "ParentToChildAssociation",
        back_populates="parent",
    )


class Child(AutoIdMixin, Base):
    __tablename__ = "right_table_children"
    name = Column(String, nullable=False)
    parents = relationship(
        "ParentToChildAssociation",
        back_populates="child",
    )


class ParentToChildAssociation(AutoIdMixin, Base):
    __table_args__ = (
        # JSON:API requires `id` field on any model,
        # so we can't create a composite PK here
        # that's why we need to create this index
        Index(
            "ix_parent_child_association_unique",
            "parent_left_id",
            "child_right_id",
            unique=True,
        ),
    )

    __tablename__ = "parent_to_child_association_table"
    parent_left_id = Column(
        ForeignKey(Parent.id),
        nullable=False,
    )
    child_right_id = Column(
        ForeignKey(Child.id),
        nullable=False,
    )
    extra_data = Column(String(50))
    parent = relationship("Parent", back_populates="children")
    child = relationship("Child", back_populates="parents")
