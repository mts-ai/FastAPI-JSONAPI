from itertools import chain
from typing import Dict, List, Optional

import pytest
from fastapi import APIRouter, Depends, FastAPI, status
from httpx import AsyncClient
from pytest_asyncio import fixture as async_fixture
from sqlalchemy import JSON, Column, ForeignKey, Index, Integer, String, Text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import declared_attr, relationship, sessionmaker

from fastapi_jsonapi import RoutersJSONAPI
from fastapi_jsonapi.exceptions.handlers import register_exception_handlers
from fastapi_jsonapi.misc.sqla.generics.base import (
    DetailViewBaseGeneric as DetailViewBaseGenericHelper,
)
from fastapi_jsonapi.misc.sqla.generics.base import (
    ListViewBaseGeneric as ListViewBaseGenericHelper,
)
from fastapi_jsonapi.querystring import QueryStringManager
from fastapi_jsonapi.schema import JSONAPIResultDetailSchema, collect_app_orm_schemas
from fastapi_jsonapi.schema_base import BaseModel, Field, RelationshipInfo
from fastapi_jsonapi.views.view_base import ViewBase
from tests.conftest import fake

pytestmark = pytest.mark.asyncio


# Schemas ⬇️⬇️⬇️
# User Schemas ⬇️


class UserBaseSchema(BaseModel):
    """User base schema."""

    class Config:
        """Pydantic schema config."""

        orm_mode = True

    name: str
    age: Optional[int] = None
    email: Optional[str] = None


class UserPatchSchema(UserBaseSchema):
    """User PATCH schema."""


class UserInSchema(UserBaseSchema):
    """User input schema."""


class UserSchema(UserInSchema):
    """User item schema."""

    id: int
    posts: List["PostSchema"] = Field(
        relationship=RelationshipInfo(
            resource_type="post",
            many=True,
        ),
    )

    bio: Optional["UserBioSchema"] = Field(
        relationship=RelationshipInfo(
            resource_type="user_bio",
        ),
    )


# User Bio Schemas ⬇️


class UserBioBaseSchema(BaseModel):
    """UserBio base schema."""

    class Config:
        """Pydantic schema config."""

        orm_mode = True

    birth_city: str
    favourite_movies: str
    keys_to_ids_list: Dict[str, List[int]] = None

    user: "UserSchema" = Field(
        relationship=RelationshipInfo(
            resource_type="user",
        ),
    )


class UserBioPatchSchema(UserBioBaseSchema):
    """UserBio PATCH schema."""


class UserBioInSchema(UserBioBaseSchema):
    """UserBio input schema."""


class UserBioSchema(UserBioInSchema):
    """UserBio item schema."""

    id: int


# Post Schemas ⬇️


class PostBaseSchema(BaseModel):
    """Post base schema."""

    class Config:
        """Pydantic schema config."""

        orm_mode = True

    title: str
    body: str


class PostPatchSchema(PostBaseSchema):
    """Post PATCH schema."""


class PostInSchema(PostBaseSchema):
    """Post input schema."""


class PostSchema(PostInSchema):
    """Post item schema."""

    id: int
    user: "UserSchema" = Field(
        relationship=RelationshipInfo(
            resource_type="user",
        ),
    )
    comments: List["PostCommentSchema"] = Field(
        relationship=RelationshipInfo(
            resource_type="post_comment",
            many=True,
        ),
    )


# Post Comment Schemas ⬇️


class PostCommentBaseSchema(BaseModel):
    """PostComment base schema."""

    class Config:
        """Pydantic schema config."""

        orm_mode = True

    text: str


class PostCommentPatchSchema(PostCommentBaseSchema):
    """PostComment PATCH schema."""


class PostCommentInSchema(PostCommentBaseSchema):
    """PostComment input schema."""


class PostCommentSchema(PostCommentInSchema):
    """PostComment item schema."""

    id: int
    post: "PostSchema" = Field(
        relationship=RelationshipInfo(
            resource_type="post",
        ),
    )
    author: "UserSchema" = Field(
        relationship=RelationshipInfo(
            resource_type="user",
        ),
    )


# Parents and Children associations ⬇️⬇️


# Association Schemas ⬇️


class ParentToChildAssociationSchema(BaseModel):
    id: int
    extra_data: str
    parent: "ParentSchema" = Field(
        relationship=RelationshipInfo(
            resource_type="parent",
        ),
    )

    child: "ChildSchema" = Field(
        relationship=RelationshipInfo(
            resource_type="child",
        ),
    )


# Parent Schemas ⬇️


class ParentBaseSchema(BaseModel):
    """Parent base schema."""

    class Config:
        """Pydantic schema config."""

        orm_mode = True

    name: str


class ParentPatchSchema(ParentBaseSchema):
    """Parent PATCH schema."""


class ParentInSchema(ParentBaseSchema):
    """Parent input schema."""


class ParentSchema(ParentInSchema):
    """Parent item schema."""

    id: int
    children: List["ParentToChildAssociationSchema"] = Field(
        relationship=RelationshipInfo(
            resource_type="parent_child_association",
            many=True,
        ),
    )


# Child Schemas ⬇️


class ChildBaseSchema(BaseModel):
    """Child base schema."""

    class Config:
        """Pydantic schema config."""

        orm_mode = True

    name: str


class ChildPatchSchema(ChildBaseSchema):
    """Child PATCH schema."""


class ChildInSchema(ChildBaseSchema):
    """Child input schema."""


class ChildSchema(ChildInSchema):
    """Child item schema."""

    id: int


# Schemas ⬆️

# DB Models ⬇️


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


# DB Models ⬆️

# DB configs ⬇️


@pytest.fixture(scope="session")
def sqla_uri():
    return "sqlite+aiosqlite:///:memory:"


# DB connections ⬇️


@async_fixture(scope="class")
async def async_engine(sqla_uri):
    engine = create_async_engine(url=make_url(sqla_uri))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    return engine


@async_fixture(scope="class")
async def async_session_plain(async_engine):
    session = sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return session


@async_fixture(scope="class")
async def async_session(async_session_plain):
    async with async_session_plain() as session:
        yield session
        # async with session.begin():


@pytest.fixture(scope="class")
def async_session_dependency(async_session_plain):
    async def get_session():
        """

        :return:
        """
        async with async_session_plain() as db_session:
            yield db_session

    return get_session


# DB connections ⬆️

# DB objects ⬇️


@async_fixture()
async def user_1(async_session: AsyncSession):
    user = User(name="john_user_1")
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    yield user
    await async_session.delete(user)
    await async_session.commit()


@async_fixture()
async def user_2(async_session: AsyncSession):
    user = User(name="sam_user_2")
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    yield user
    await async_session.delete(user)
    await async_session.commit()


@async_fixture()
async def user_1_bio(async_session: AsyncSession, user_1):
    bio = UserBio(
        birth_city="Moscow",
        favourite_movies="Django, Alien",
        keys_to_ids_list={"key": [1, 2, 3]},
        user=user_1,
    )
    async_session.add(bio)
    await async_session.commit()
    await async_session.refresh(bio)
    yield bio
    await async_session.delete(bio)
    await async_session.commit()


@async_fixture()
async def user_1_posts(async_session: AsyncSession, user_1: User):
    posts = [Post(title=f"post_u1_{i}", user=user_1) for i in range(1, 4)]
    async_session.add_all(posts)
    await async_session.commit()

    for post in posts:
        await async_session.refresh(post)

    yield posts

    for post in posts:
        await async_session.delete(post)
    await async_session.commit()


@async_fixture()
async def user_2_posts(async_session: AsyncSession, user_2: User):
    posts = [Post(title=f"post_u2_{i}", user=user_2) for i in range(1, 5)]
    async_session.add_all(posts)
    await async_session.commit()

    for post in posts:
        await async_session.refresh(post)

    yield posts

    for post in posts:
        await async_session.delete(post)
    await async_session.commit()


@async_fixture()
async def user_1_comments_for_u2_posts(async_session: AsyncSession, user_1, user_2_posts):
    post_comments = [
        PostComment(
            text=f"comment_{i}_for_post_{post.id}",
            post=post,
            author=user_1,
        )
        for i, post in enumerate(user_2_posts, start=1)
    ]
    async_session.add_all(post_comments)
    await async_session.commit()

    for comment in post_comments:
        await async_session.refresh(comment)

    yield post_comments

    for comment in post_comments:
        await async_session.delete(comment)
    await async_session.commit()


@pytest.fixture()
def user_1_post_for_comments(user_1_posts: List[Post]) -> Post:
    return user_1_posts[0]


@async_fixture()
async def user_2_comment_for_one_u1_post(async_session: AsyncSession, user_2, user_1_post_for_comments):
    post = user_1_post_for_comments
    post_comment = PostComment(
        text=f"one_comment_from_u2_for_post_{post.id}",
        post=post,
        author=user_2,
    )
    async_session.add(post_comment)
    await async_session.commit()

    await async_session.refresh(post_comment)

    yield post_comment

    await async_session.delete(post_comment)
    await async_session.commit()


@async_fixture()
async def parent_1(async_session: AsyncSession):
    parent = Parent(
        name="parent_1",
    )
    async_session.add(parent)
    await async_session.commit()

    await async_session.refresh(parent)

    yield parent

    await async_session.delete(parent)
    await async_session.commit()


@async_fixture()
async def parent_2(async_session: AsyncSession):
    parent = Parent(
        name="parent_2",
    )
    async_session.add(parent)
    await async_session.commit()

    await async_session.refresh(parent)

    yield parent

    await async_session.delete(parent)
    await async_session.commit()


@async_fixture()
async def parent_3(async_session: AsyncSession):
    parent = Parent(
        name="parent_3",
    )
    async_session.add(parent)
    await async_session.commit()

    await async_session.refresh(parent)

    yield parent

    await async_session.delete(parent)
    await async_session.commit()


@async_fixture()
async def child_1(async_session: AsyncSession):
    child = Child(
        name="child_1",
    )
    async_session.add(child)
    await async_session.commit()

    await async_session.refresh(child)

    yield child

    await async_session.delete(child)
    await async_session.commit()


@async_fixture()
async def child_2(async_session: AsyncSession):
    child = Child(
        name="child_2",
    )
    async_session.add(child)
    await async_session.commit()

    await async_session.refresh(child)

    yield child

    await async_session.delete(child)
    await async_session.commit()


@async_fixture()
async def child_3(async_session: AsyncSession):
    child = Child(
        name="child_3",
    )
    async_session.add(child)
    await async_session.commit()

    await async_session.refresh(child)

    yield child

    await async_session.delete(child)
    await async_session.commit()


@async_fixture()
async def child_4(async_session: AsyncSession):
    child = Child(
        name="child_4",
    )
    async_session.add(child)
    await async_session.commit()

    await async_session.refresh(child)

    yield child

    await async_session.delete(child)
    await async_session.commit()


@async_fixture()
async def p1_c1_association(
    async_session: AsyncSession,
    parent_1: Parent,
    child_1: Child,
):
    assoc = ParentToChildAssociation(
        parent=parent_1,
        child=child_1,
        extra_data="assoc_p1c1_extra",
    )
    async_session.add(assoc)
    await async_session.commit()

    await async_session.refresh(assoc)

    yield assoc

    await async_session.delete(assoc)
    await async_session.commit()


@async_fixture()
async def p2_c1_association(
    async_session: AsyncSession,
    parent_2: Parent,
    child_1: Child,
):
    assoc = ParentToChildAssociation(
        parent=parent_2,
        child=child_1,
        extra_data="assoc_p2c1_extra",
    )
    async_session.add(assoc)
    await async_session.commit()

    await async_session.refresh(assoc)

    yield assoc

    await async_session.delete(assoc)
    await async_session.commit()


@async_fixture()
async def p1_c2_association(
    async_session: AsyncSession,
    parent_1: Parent,
    child_2: Child,
):
    assoc = ParentToChildAssociation(
        parent=parent_1,
        child=child_2,
        extra_data="assoc_p1c2_extra",
    )
    async_session.add(assoc)
    await async_session.commit()

    await async_session.refresh(assoc)

    yield assoc

    await async_session.delete(assoc)
    await async_session.commit()


@async_fixture()
async def p2_c2_association(
    async_session: AsyncSession,
    parent_2: Parent,
    child_2: Child,
):
    assoc = ParentToChildAssociation(
        parent=parent_2,
        child=child_2,
        extra_data="assoc_p2c2_extra",
    )
    async_session.add(assoc)
    await async_session.commit()

    await async_session.refresh(assoc)

    yield assoc

    await async_session.delete(assoc)
    await async_session.commit()


@async_fixture()
async def p2_c3_association(
    async_session: AsyncSession,
    parent_2: Parent,
    child_3: Child,
):
    assoc = ParentToChildAssociation(
        parent=parent_2,
        child=child_3,
        extra_data="assoc_p2c3_extra",
    )
    async_session.add(assoc)
    await async_session.commit()

    await async_session.refresh(assoc)

    yield assoc

    await async_session.delete(assoc)
    await async_session.commit()


# DB objects ⬆️

# Views ⬇️⬇️


@pytest.fixture(scope="class")
def detail_view_base_generic(async_session_dependency):
    class DetailViewBaseGeneric(DetailViewBaseGenericHelper):
        async def init_dependencies(self, session: AsyncSession = Depends(async_session_dependency)):
            self.session = session

    return DetailViewBaseGeneric


@pytest.fixture(scope="class")
def list_view_base_generic(async_session_dependency):
    class ListViewBaseGeneric(ListViewBaseGenericHelper):
        async def init_dependencies(self, session: AsyncSession = Depends(async_session_dependency)):
            self.session = session

    return ListViewBaseGeneric


@pytest.fixture(scope="class")
def list_view_base_generic_helper_for_sqla(async_session_dependency):
    class ListViewBaseGeneric(ListViewBaseGenericHelper):
        async def init_dependencies(self, session: AsyncSession = Depends(async_session_dependency)):
            self.session = session

        # TODO: remove, use generic
        async def post(
            self,
            data: UserInSchema,
            query_params: QueryStringManager,
            session: AsyncSession = Depends(async_session_dependency),
        ) -> JSONAPIResultDetailSchema:
            user_obj: User = await self.create_object(
                data_create=data.dict(),
                view_kwargs={},
                session=session,
            )

            return await self.get_resource_detail_result(object_id=user_obj.id)

    return ListViewBaseGeneric


# User ⬇️


@pytest.fixture(scope="class")
def user_detail_view(detail_view_base_generic):
    """
    :param detail_view_base_generic:
    :return:
    """

    class UserDetail(detail_view_base_generic):
        ...

    return UserDetail


@pytest.fixture(scope="class")
def user_list_view(list_view_base_generic, async_session_dependency):
    """
    :param list_view_base_generic:
    :param async_session_dependency:
    :return:
    """

    class UserList(list_view_base_generic):
        # todo: remove
        async def post(
            self,
            data: UserInSchema,
            query_params: QueryStringManager,
            session: AsyncSession = Depends(async_session_dependency),
        ) -> JSONAPIResultDetailSchema:
            user_obj: User = await self.create_object(
                data_create=data.dict(),
                view_kwargs={},
                session=session,
            )

            return await self.get_detail_view_result(
                query_params=query_params,
                view_kwargs={"id": user_obj.id},
                session=session,
            )

    return UserList


@pytest.fixture(scope="class")
def user_list_view_generic(list_view_base_generic_helper_for_sqla):
    """
    :param list_view_base_generic_helper_for_sqla:
    :return:
    """

    class UserList(list_view_base_generic_helper_for_sqla):
        ...

    return UserList


# User Bio ⬇️


@pytest.fixture(scope="class")
def user_bio_detail_view(detail_view_base_generic):
    """
    :param detail_view_base_generic:
    :return:
    """

    class UserBioDetail(detail_view_base_generic):
        ...

    return UserBioDetail


@pytest.fixture(scope="class")
def user_detail_view_sync(detail_view_base_generic):
    """
    :param detail_view_base_generic:
    :return:
    """

    class UserDetail(detail_view_base_generic):
        def get(self):
            return {"ok": True}

    return UserDetail


@pytest.fixture(scope="class")
def user_bio_list_view(list_view_base_generic):
    """
    :param list_view_base_generic:
    :return:
    """

    class UserBioList(list_view_base_generic):
        ...

    return UserBioList


# Post ⬇️


@pytest.fixture(scope="class")
def post_detail_view(detail_view_base_generic):
    """
    :param detail_view_base_generic:
    :return:
    """

    class PostDetail(detail_view_base_generic):
        ...

    return PostDetail


@pytest.fixture(scope="class")
def post_list_view(list_view_base_generic):
    """
    :param list_view_base_generic:
    :return:
    """

    class PostList(list_view_base_generic):
        ...

    return PostList


# Parent ⬇️


@pytest.fixture(scope="class")
def parent_detail_view(detail_view_base_generic):
    """
    :param detail_view_base_generic:
    :return:
    """

    class ParentDetail(detail_view_base_generic):
        ...

    return ParentDetail


@pytest.fixture(scope="class")
def parent_list_view(list_view_base_generic):
    """
    :param list_view_base_generic:
    :return:
    """

    class ParentList(list_view_base_generic):
        ...

    return ParentList


# Child ⬇️


@pytest.fixture(scope="class")
def child_detail_view(detail_view_base_generic):
    """
    :param detail_view_base_generic:
    :return:
    """

    class ChildDetail(detail_view_base_generic):
        ...

    return ChildDetail


@pytest.fixture(scope="class")
def child_list_view(list_view_base_generic):
    """
    :param list_view_base_generic:
    :return:
    """

    class ChildList(list_view_base_generic):
        ...

    return ChildList


# Views ⬆️


# app ⬇️


@pytest.fixture()
def app_max_include_depth():
    return 5


@pytest.fixture()
def app_plain(app_max_include_depth) -> FastAPI:
    app = FastAPI(
        title="FastAPI and SQLAlchemy",
        debug=True,
        openapi_url="/openapi.json",
        docs_url="/docs",
    )
    app.config = {"MAX_INCLUDE_DEPTH": app_max_include_depth}
    collect_app_orm_schemas(app)
    return app


# Routing ⬇️


@pytest.fixture()
def app(
    app_plain: FastAPI,
    user_detail_view,
    user_list_view,
    user_bio_detail_view,
    user_bio_list_view,
    post_detail_view,
    post_list_view,
    parent_detail_view,
    parent_list_view,
    child_detail_view,
    child_list_view,
):
    router: APIRouter = APIRouter()
    RoutersJSONAPI(
        router=router,
        path="/users",
        tags=["User"],
        class_detail=user_detail_view,
        class_list=user_list_view,
        schema=UserSchema,
        resource_type="user",
        schema_in_patch=UserPatchSchema,
        schema_in_post=UserInSchema,
        model=User,
    )

    RoutersJSONAPI(
        router=router,
        path="/posts",
        tags=["Post"],
        class_detail=post_detail_view,
        class_list=post_list_view,
        schema=PostSchema,
        resource_type="post",
        schema_in_patch=PostPatchSchema,
        schema_in_post=PostInSchema,
        model=Post,
    )

    RoutersJSONAPI(
        router=router,
        path="/user-bio",
        tags=["Bio"],
        class_detail=user_bio_detail_view,
        class_list=user_bio_list_view,
        schema=UserBioSchema,
        resource_type="user_bio",
        schema_in_patch=UserBioPatchSchema,
        schema_in_post=UserBioInSchema,
        model=UserBio,
    )

    RoutersJSONAPI(
        router=router,
        path="/parents",
        tags=["Parent"],
        class_detail=parent_detail_view,
        class_list=parent_list_view,
        schema=ParentSchema,
        resource_type="parent",
        schema_in_patch=ParentPatchSchema,
        schema_in_post=ParentPatchSchema,
        model=Parent,
    )

    RoutersJSONAPI(
        router=router,
        path="/children",
        tags=["Child"],
        class_detail=child_detail_view,
        class_list=child_list_view,
        schema=ChildSchema,
        resource_type="child",
        schema_in_patch=ChildPatchSchema,
        schema_in_post=ChildInSchema,
        model=Child,
    )

    app_plain.include_router(router, prefix="")
    register_exception_handlers(app_plain)

    return app_plain


@pytest.fixture()
def app2(
    app_plain: FastAPI,
    user_detail_view_sync,
    user_list_view_generic,
):
    router: APIRouter = APIRouter()
    RoutersJSONAPI(
        router=router,
        path="/users",
        tags=["User"],
        class_detail=user_detail_view_sync,
        class_list=user_list_view_generic,
        schema=UserSchema,
        resource_type="user",
        schema_in_patch=UserPatchSchema,
        schema_in_post=UserInSchema,
        model=User,
    )

    app_plain.include_router(router, prefix="")

    return app_plain


@async_fixture()
async def client(app: FastAPI) -> AsyncClient:
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@async_fixture()
async def client2(app2: FastAPI) -> AsyncClient:
    async with AsyncClient(app=app2, base_url="http://test") as ac:
        yield ac


# app ⬆️


def association_key(data: dict):
    return data["type"], data["id"]


async def test_root(client: AsyncClient):
    response = await client.get("/docs")
    assert response.status_code == status.HTTP_200_OK


async def test_get_users(client: AsyncClient, user_1: User, user_2: User):
    response = await client.get("/users")
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert "data" in response_data, response_data
    users_data = response_data["data"]
    users = [user_1, user_2]
    assert len(users_data) == len(users)
    for user_data, user in zip(users_data, users):
        assert user_data["id"] == ViewBase.get_db_item_id(user)
        assert user_data["type"] == "user"


async def test_get_user_with_bio_relation(
    client: AsyncClient,
    user_1: User,
    user_1_bio: UserBio,
):
    url = f"/users/{user_1.id}?include=bio"
    response = await client.get(url)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert "data" in response_data, response_data
    assert response_data["data"]["id"] == ViewBase.get_db_item_id(user_1)
    assert response_data["data"]["type"] == "user"
    assert "included" in response_data, response_data
    included_bio = response_data["included"][0]
    assert included_bio["id"] == ViewBase.get_db_item_id(user_1_bio)
    assert included_bio["type"] == "user_bio"


async def test_get_users_with_bio_relation(
    client: AsyncClient,
    user_1: User,
    user_2: User,
    user_1_bio: UserBio,
):
    url = "/users?include=bio"
    response = await client.get(url)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert "data" in response_data, response_data
    users_data = response_data["data"]
    users = [user_1, user_2]
    assert len(users_data) == len(users)
    for user_data, user in zip(users_data, users):
        assert user_data["id"] == ViewBase.get_db_item_id(user)
        assert user_data["type"] == "user"

    assert "included" in response_data, response_data
    included_bio = response_data["included"][0]
    assert included_bio["id"] == ViewBase.get_db_item_id(user_1_bio)
    assert included_bio["type"] == "user_bio"


async def test_get_posts_with_users(
    client: AsyncClient,
    user_1: User,
    user_2: User,
    user_1_posts: List[Post],
    user_2_posts: List[Post],
):
    url = "/posts?include=user"
    response = await client.get(url)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert "data" in response_data, response_data
    u1_posts = list(user_1_posts)
    u2_posts = list(user_2_posts)
    posts = list(chain(u1_posts, u2_posts))

    posts_data = list(response_data["data"])
    assert len(posts) == len(posts_data)

    assert "included" in response_data, response_data
    users = [user_1, user_2]
    included_users = response_data["included"]
    assert len(included_users) == len(users)
    for user_data, user in zip(included_users, users):
        assert user_data["id"] == ViewBase.get_db_item_id(user)
        assert user_data["type"] == "user"

    for post_data, post in zip(posts_data, posts):
        assert post_data["id"] == ViewBase.get_db_item_id(post)
        assert post_data["type"] == "post"

    all_posts_data = list(posts_data)
    idx_start = 0
    for posts, user in [
        (u1_posts, user_1),
        (u2_posts, user_2),
    ]:
        next_idx = len(posts) + idx_start
        posts_data = all_posts_data[idx_start:next_idx]

        assert len(posts_data) == len(posts)
        idx_start = next_idx

        u1_relation = {
            "id": ViewBase.get_db_item_id(user),
            "type": "user",
        }
        for post_data in posts_data:
            user_relation = post_data["relationships"]["user"]
            assert user_relation["data"] == u1_relation


async def test_get_users_with_all_inner_relations(
    client: AsyncClient,
    user_1: User,
    user_2: User,
    user_1_bio: UserBio,
    user_1_posts,
    user_1_post_for_comments: Post,
    user_2_posts: List[Post],
    user_1_comments_for_u2_posts: List[PostComment],
    user_2_comment_for_one_u1_post: PostComment,
):
    """
    Include:
    - bio
    - posts
    - posts.comments
    - posts.comments.author
    """
    url = "/users?include=bio,posts,posts.comments,posts.comments.author"
    response = await client.get(url)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert "data" in response_data, response_data

    users = [user_1, user_2]
    users_data = response_data["data"]
    assert len(users_data) == len(users)

    assert "included" in response_data, response_data
    included: List[Dict] = response_data["included"]

    included_data = {association_key(data): data for data in included}

    for user_data, (user, user_posts, expected_bio) in zip(
        users_data,
        [(user_1, user_1_posts, user_1_bio), (user_2, user_2_posts, None)],
    ):
        assert user_data["id"] == ViewBase.get_db_item_id(user)
        assert user_data["type"] == "user"
        user_relationships = user_data["relationships"]
        posts_relation = user_relationships["posts"]["data"]
        assert len(posts_relation) == len(user_posts)
        for post_relation in posts_relation:
            assert association_key(post_relation) in included_data

        bio_relation = user_relationships["bio"]["data"]
        if bio_relation is None:
            # bio may be not present
            assert expected_bio is None
            continue

        assert bio_relation == {
            "id": ViewBase.get_db_item_id(user_1_bio),
            "type": "user_bio",
        }

    # ! assert posts have expected post comments
    for posts, comments, comment_author in [
        ([user_1_post_for_comments], [user_2_comment_for_one_u1_post], user_2),
        (user_2_posts, user_1_comments_for_u2_posts, user_1),
    ]:
        for post, post_comment in zip(posts, comments):
            post_data = included_data[("post", ViewBase.get_db_item_id(post))]
            post_relationships = post_data["relationships"]
            assert "comments" in post_relationships
            post_comments_relation = post_relationships["comments"]["data"]
            post_comments = [post_comment]
            assert len(post_comments_relation) == len(post_comments)
            for comment_relation_data, comment in zip(post_comments_relation, post_comments):
                assert comment_relation_data == {
                    "id": ViewBase.get_db_item_id(comment),
                    "type": "post_comment",
                }

                comment_data = included_data[("post_comment", ViewBase.get_db_item_id(comment))]
                assert comment_data["relationships"]["author"]["data"] == {
                    "id": ViewBase.get_db_item_id(comment_author),
                    "type": "user",
                }
                assert ("user", ViewBase.get_db_item_id(comment_author)) in included_data


async def test_many_to_many_load_inner_includes_to_parents(
    client: AsyncClient,
    parent_1,
    parent_2,
    parent_3,
    child_1,
    child_2,
    child_3,
    child_4,
    p1_c1_association,
    p2_c1_association,
    p1_c2_association,
    p2_c2_association,
    p2_c3_association,
):
    url = "/parents?include=children,children.child"
    response = await client.get(url)
    assert response.status_code == status.HTTP_200_OK, response
    response_data = response.json()
    parents_data = response_data["data"]
    parents = [parent_1, parent_2, parent_3]
    assert len(parents_data) == len(parents)

    included = response_data["included"]
    included_data = {(data["type"], data["id"]): data for data in included}

    for parent_data, (parent, expected_assocs) in zip(
        parents_data,
        [
            (parent_1, [(p1_c1_association, child_1), (p1_c2_association, child_2)]),
            (parent_2, [(p2_c1_association, child_1), (p2_c2_association, child_2), (p2_c3_association, child_3)]),
            (parent_3, []),
        ],
    ):
        assert parent_data["id"] == ViewBase.get_db_item_id(parent)
        assert parent_data["type"] == "parent"

        parent_relationships = parent_data["relationships"]
        parent_to_children_assocs = parent_relationships["children"]["data"]
        assert len(parent_to_children_assocs) == len(expected_assocs)
        for assoc_data, (assoc, child) in zip(parent_to_children_assocs, expected_assocs):
            assert assoc_data["id"] == ViewBase.get_db_item_id(assoc)
            assert assoc_data["type"] == "parent_child_association"
            assoc_key = association_key(assoc_data)
            assert assoc_key in included_data
            p_to_c_assoc_data = included_data[assoc_key]
            assert p_to_c_assoc_data["relationships"]["child"]["data"] == {
                "id": ViewBase.get_db_item_id(child),
                "type": "child",
            }
            assert p_to_c_assoc_data["attributes"]["extra_data"] == assoc.extra_data

    assert ("child", ViewBase.get_db_item_id(child_4)) not in included_data


async def test_method_not_allowed(client: AsyncClient):
    res = await client.put("/users", json={})
    assert res.status_code == status.HTTP_405_METHOD_NOT_ALLOWED, res.status_code


async def test_create_user(client: AsyncClient):
    create_user_data = UserInSchema(
        name=fake.name(),
        age=fake.pyint(),
        email=fake.email(),
    )
    res = await client.post("/users", json={"attributes": create_user_data.dict()})
    assert res.status_code == status.HTTP_201_CREATED, res.text
    response_data = res.json()
    assert "data" in response_data, response_data
    assert response_data["data"]["attributes"] == create_user_data.dict()


async def test_create_user_and_fetch_data(client: AsyncClient):
    create_user_data = UserInSchema(
        name=fake.name(),
        age=fake.pyint(),
        email=fake.email(),
    )
    res = await client.post("/users", json={"attributes": create_user_data.dict()})
    assert res.status_code == status.HTTP_201_CREATED, res.text
    response_data = res.json()
    assert "data" in response_data, response_data
    assert response_data["data"]["attributes"] == create_user_data.dict()

    user_id = response_data["data"]["id"]

    res = await client.get(f"/users/{user_id}")
    assert res.status_code == status.HTTP_200_OK, res.text
    response_data = res.json()
    assert "data" in response_data, response_data
    assert response_data["data"]["attributes"] == create_user_data.dict()
    assert response_data["data"]["id"] == user_id


async def test_get_user_not_found(client: AsyncClient):
    fake_id = 1
    res = await client.get(f"/users/{fake_id}")

    assert res.json() == {
        "errors": [
            {
                "detail": "Resource User `1` not found",
                "title": "Resource not found.",
                "status_code": 404,
                "meta": {"parameter": "id"},
            },
        ],
    }


class TestApp2:
    async def test_sync_view(self, client2: AsyncClient):
        res = await client2.get("/users/0")
        assert res
        assert res.status_code == status.HTTP_200_OK
        assert res.json() == {"ok": True}

    async def test_get_list_view_generic(self, client2: AsyncClient, user_1: User):
        res = await client2.get("/users")
        assert res
        assert res.status_code == status.HTTP_200_OK
        response_json = res.json()
        users_data = response_json["data"]
        assert len(users_data) == 1, users_data
        user_data = users_data[0]
        assert user_data["id"] == str(user_1.id)
        assert user_data["attributes"] == UserBaseSchema.from_orm(user_1)

    async def test_create_object(self, client2: AsyncClient):
        create_user_data = UserInSchema(
            name=fake.name(),
            age=fake.pyint(),
            email=fake.email(),
        )
        res = await client2.post("/users", json={"attributes": create_user_data.dict()})
        assert res.status_code == status.HTTP_201_CREATED, res.text
        response_data = res.json()
        assert "data" in response_data, response_data
        assert response_data["data"]["attributes"] == create_user_data.dict()


# todo: test filters
# todo: test sorts
# todo: test object not found
