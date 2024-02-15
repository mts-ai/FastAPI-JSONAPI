from typing import TYPE_CHECKING, Dict, List, Optional
from uuid import UUID

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import declared_attr, relationship
from sqlalchemy.types import CHAR, TypeDecorator

from tests.common import is_postgres_tests, sqla_uri


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

    posts = relationship(
        "Post",
        back_populates="user",
        uselist=True,
        cascade="all,delete",
    )
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
    computers = relationship(
        "Computer",
        # TODO: rename
        # back_populates="owner",
        back_populates="user",
        uselist=True,
    )
    workplace = relationship(
        "Workplace",
        back_populates="user",
        uselist=False,
    )
    if TYPE_CHECKING:
        computers: list["Computer"]

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


class Computer(AutoIdMixin, Base):
    """
    Model for check many-to-one relationships update
    """

    __tablename__ = "computers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    # TODO: rename
    # owner = relationship("User", back_populates="computers")
    user = relationship("User", back_populates="computers")

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id}, name={self.name!r}, user_id={self.user_id})"


class Workplace(AutoIdMixin, Base):
    """
    Model for check one-to-one relationships update
    """

    __tablename__ = "workplaces"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user = relationship("User", back_populates="workplace")

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id}, name={self.name!r}, user_id={self.user_id})"


class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True)
    task_ids = Column(JSON, nullable=True, unique=False)


# uuid below


class CustomUUIDType(TypeDecorator):
    cache_ok = True

    impl = CHAR

    def __init__(self, *args, as_uuid=True, **kwargs):
        """
        Construct a UUID type.

        # TODO: support as_uuid=False (and set by default!)
        :param as_uuid=True: if True, values will be interpreted
         as Python uuid objects, converting to/from string via theDBAPI.

        """
        super().__init__(*args, **kwargs)
        self.as_uuid = as_uuid

    def load_dialect_impl(self, dialect):
        return CHAR(32)

    def process_bind_param(self, value, dialect):
        if value is None:
            return value

        if not isinstance(value, UUID):
            msg = f"Incorrect type got {type(value).__name__}, expected {UUID.__name__}"
            raise Exception(msg)

        return str(value)

    def process_result_value(self, value, dialect):
        return value and UUID(value)

    @property
    def python_type(self):
        return UUID if self.as_uuid else str


db_uri = sqla_uri()
if is_postgres_tests():
    # noinspection PyPep8Naming
    from sqlalchemy.dialects.postgresql.asyncpg import AsyncpgUUID as UUIDType
elif "sqlite" in db_uri:
    UUIDType = CustomUUIDType
else:
    msg = "unsupported dialect (custom uuid?)"
    raise ValueError(msg)


class CustomUUIDItem(Base):
    __tablename__ = "custom_uuid_item"
    id = Column(UUIDType(as_uuid=True), primary_key=True)

    extra_id = Column(
        UUIDType(as_uuid=True),
        nullable=True,
        unique=True,
    )


class SelfRelationship(Base):
    id = Column(Integer, primary_key=True)
    name = Column(String)
    self_relationship_id = Column(
        Integer,
        ForeignKey(
            "selfrelationships.id",
            name="fk_self_relationship_id",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=True,
    )
    # parent = relationship("SelfRelationship", back_populates="s")
    self_relationship = relationship("SelfRelationship", remote_side=[id])


class ContainsTimestamp(Base):
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime(True), nullable=False)


class Alpha(Base):
    __tablename__ = "alpha"

    id = Column(Integer, primary_key=True, autoincrement=True)
    beta_id = Column(
        Integer,
        ForeignKey("beta.id"),
        nullable=False,
        index=True,
    )
    beta = relationship("Beta", back_populates="alphas")
    gamma_id = Column(Integer, ForeignKey("gamma.id"), nullable=False)
    gamma: "Gamma" = relationship("Gamma")


class BetaGammaBinding(Base):
    __tablename__ = "beta_gamma_binding"

    id: int = Column(Integer, primary_key=True)
    beta_id: int = Column(ForeignKey("beta.id", ondelete="CASCADE"), nullable=False)
    gamma_id: int = Column(ForeignKey("gamma.id", ondelete="CASCADE"), nullable=False)


class Beta(Base):
    __tablename__ = "beta"

    id = Column(Integer, primary_key=True, autoincrement=True)
    gammas: List["Gamma"] = relationship(
        "Gamma",
        secondary="beta_gamma_binding",
        back_populates="betas",
        lazy="noload",
    )
    alphas = relationship("Alpha")
    deltas: List["Delta"] = relationship(
        "Delta",
        secondary="beta_delta_binding",
        lazy="noload",
    )


class Gamma(Base):
    __tablename__ = "gamma"

    id = Column(Integer, primary_key=True, autoincrement=True)
    betas: List["Beta"] = relationship(
        "Beta",
        secondary="beta_gamma_binding",
        back_populates="gammas",
        lazy="raise",
    )
    delta_id: int = Column(
        Integer,
        ForeignKey("delta.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alpha = relationship("Alpha")
    delta: "Delta" = relationship("Delta")


class BetaDeltaBinding(Base):
    __tablename__ = "beta_delta_binding"

    id: int = Column(Integer, primary_key=True)
    beta_id: int = Column(ForeignKey("beta.id", ondelete="CASCADE"), nullable=False)
    delta_id: int = Column(ForeignKey("delta.id", ondelete="CASCADE"), nullable=False)


class Delta(Base):
    __tablename__ = "delta"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    gammas: List["Gamma"] = relationship("Gamma", back_populates="delta", lazy="noload")
    betas: List["Beta"] = relationship("Beta", secondary="beta_delta_binding", back_populates="deltas", lazy="noload")
