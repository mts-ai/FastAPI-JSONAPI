from itertools import chain
from typing import Dict, List, Optional

import pytest
from fastapi import APIRouter, Depends, FastAPI, status
from httpx import AsyncClient
from pytest_asyncio import fixture as async_fixture
from sqlalchemy import JSON, Column, ForeignKey, Integer, String, Text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import declared_attr, relationship, sessionmaker

from fastapi_jsonapi import RoutersJSONAPI, SqlalchemyEngine
from fastapi_jsonapi.data_layers.orm import DBORMType
from fastapi_jsonapi.querystring import QueryStringManager
from fastapi_jsonapi.schema import JSONAPIResultDetailSchema, JSONAPIResultListSchema, collect_app_orm_schemas
from fastapi_jsonapi.schema_base import BaseModel, Field, RelationshipInfo
from fastapi_jsonapi.views.detail_view import DetailViewBase
from fastapi_jsonapi.views.list_view import ListViewBase

pytestmark = pytest.mark.asyncio


# Schemas ⬇️⬇️⬇️
# User Schemas ⬇️


class UserBaseSchema(BaseModel):
    """User base schema."""

    class Config:
        """Pydantic schema config."""

        orm_mode = True

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    age: Optional[int] = None
    email: str | None = None


class UserPatchSchema(UserBaseSchema):
    """User PATCH schema."""


class UserInSchema(UserBaseSchema):
    """User input schema."""


class UserSchema(UserInSchema):
    """User item schema."""

    class Config:
        """Pydantic model config."""

        orm_mode = True

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

    user_id: str
    birth_city: str
    favourite_movies: str
    keys_to_ids_list: Dict[str, List[int]] = None


class UserBioPatchSchema(UserBioBaseSchema):
    """UserBio PATCH schema."""


class UserBioInSchema(UserBioBaseSchema):
    """UserBio input schema."""


class UserBioSchema(UserBioInSchema):
    """UserBio item schema."""

    class Config:
        """Pydantic model config."""

        orm_mode = True

    id: int

    user: "UserSchema" = Field(
        relationship=RelationshipInfo(
            resource_type="user",
        ),
    )


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

    class Config:
        """Pydantic model config."""

        orm_mode = True

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

    class Config:
        """Pydantic model config."""

        orm_mode = True

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

    @declared_attr
    def id(cls):
        return Column(Integer, primary_key=True, autoincrement=True)


Base = declarative_base(cls=Base)


class User(Base):
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


class UserBio(Base):
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


class Post(Base):
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


class PostComment(Base):
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


# DB Models ⬆️

# DB configs ⬇️


@pytest.fixture(scope="session")
def sqla_uri():
    return "sqlite+aiosqlite:///:memory:"


# DB connections ⬇️


@async_fixture(scope="module")
async def async_engine(sqla_uri):
    engine = create_async_engine(url=make_url(sqla_uri))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    return engine


@async_fixture(scope="module")
async def async_session_plain(async_engine):
    session = sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return session


@async_fixture(scope="module")
async def async_session(async_session_plain):
    async with async_session_plain() as session:
        yield session
        # async with session.begin():


@pytest.fixture(scope="module")
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


# DB objects ⬆️

# Views ⬇️⬇️
# User ⬇️


@pytest.fixture(scope="module")
def user_detail_view(async_session_dependency):
    """
    TODO: patch
    :param async_session_dependency:
    :return:
    """

    class UserDetail(DetailViewBase):
        async def get(
            self,
            obj_id,
            query_params: QueryStringManager,
            session: AsyncSession = Depends(async_session_dependency),
        ) -> JSONAPIResultDetailSchema:
            dl = SqlalchemyEngine(
                schema=self.jsonapi.schema_detail,
                model=self.jsonapi.model,
                session=session,
            )
            view_kwargs = {"id": obj_id}
            return await self.get_detailed_result(
                dl=dl,
                view_kwargs=view_kwargs,
                query_params=query_params,
            )

    return UserDetail


@pytest.fixture(scope="module")
def user_list_view(async_session_dependency):
    """
    TODO: post
    :param async_session_dependency:
    :return:
    """

    class UserList(ListViewBase):
        async def get(
            self,
            query_params: QueryStringManager,
            session: AsyncSession = Depends(async_session_dependency),
        ) -> JSONAPIResultListSchema:
            dl = SqlalchemyEngine(
                schema=self.jsonapi.schema_list,
                model=self.jsonapi.model,
                session=session,
            )
            return await self.get_paginated_result(
                dl=dl,
                query_params=query_params,
            )

    return UserList


# User Bio ⬇️


@pytest.fixture(scope="module")
def user_bio_detail_view(async_session_dependency):
    """
    TODO: patch
    :param async_session_dependency:
    :return:
    """

    class UserBioDetail(DetailViewBase):
        async def get(
            self,
            obj_id,
            query_params: QueryStringManager,
            session: AsyncSession = Depends(async_session_dependency),
        ) -> JSONAPIResultDetailSchema:
            dl = SqlalchemyEngine(
                schema=self.jsonapi.schema_detail,
                model=self.jsonapi.model,
                session=session,
            )
            view_kwargs = {"id": obj_id}
            return await self.get_detailed_result(
                dl=dl,
                view_kwargs=view_kwargs,
                query_params=query_params,
            )

    return UserBioDetail


@pytest.fixture(scope="module")
def user_bio_list_view(async_session_dependency):
    """
    TODO: post
    :param async_session_dependency:
    :return:
    """

    class UserBioList(ListViewBase):
        async def get(
            self,
            query_params: QueryStringManager,
            session: AsyncSession = Depends(async_session_dependency),
        ) -> JSONAPIResultListSchema:
            dl = SqlalchemyEngine(
                schema=self.jsonapi.schema_list,
                model=self.jsonapi.model,
                session=session,
            )
            return await self.get_paginated_result(
                dl=dl,
                query_params=query_params,
            )

    return UserBioList


# Post ⬇️


@pytest.fixture(scope="module")
def post_detail_view(async_session_dependency):
    """
    TODO: patch
    :param async_session_dependency:
    :return:
    """

    class PostDetail(DetailViewBase):
        async def get(
            self,
            obj_id,
            query_params: QueryStringManager,
            session: AsyncSession = Depends(async_session_dependency),
        ) -> JSONAPIResultDetailSchema:
            dl = SqlalchemyEngine(
                schema=self.jsonapi.schema_detail,
                model=self.jsonapi.model,
                session=session,
            )
            view_kwargs = {"id": obj_id}
            return await self.get_detailed_result(
                dl=dl,
                view_kwargs=view_kwargs,
                query_params=query_params,
            )

    return PostDetail


@pytest.fixture(scope="module")
def post_list_view(async_session_dependency):
    """
    TODO: post
    :param async_session_dependency:
    :return:
    """

    class PostList(ListViewBase):
        async def get(
            self,
            query_params: QueryStringManager,
            session: AsyncSession = Depends(async_session_dependency),
        ) -> JSONAPIResultListSchema:
            dl = SqlalchemyEngine(
                schema=self.jsonapi.schema_list,
                model=self.jsonapi.model,
                session=session,
            )
            return await self.get_paginated_result(
                dl=dl,
                query_params=query_params,
            )

    return PostList


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
):
    # tags = [
    #     {
    #         "name": "User",
    #         "description": "Users API",
    #     },
    #     {
    #         "name": "Bio",
    #         "description": "User Bio API",
    #     },
    #     {
    #         "name": "Post",
    #         "description": "Posts API",
    #     },
    # ]

    router: APIRouter = APIRouter()
    RoutersJSONAPI(
        routers=router,
        path="/users",
        tags=["User"],
        class_detail=user_detail_view,
        class_list=user_list_view,
        schema=UserSchema,
        type_resource="user",
        schema_in_patch=UserPatchSchema,
        schema_in_post=UserInSchema,
        model=User,
        engine=DBORMType.sqlalchemy,
    )

    RoutersJSONAPI(
        routers=router,
        path="/posts",
        tags=["Post"],
        class_detail=post_detail_view,
        class_list=post_list_view,
        schema=PostSchema,
        type_resource="post",
        schema_in_patch=PostPatchSchema,
        schema_in_post=PostInSchema,
        model=Post,
        engine=DBORMType.sqlalchemy,
    )

    RoutersJSONAPI(
        routers=router,
        path="/user-bio",
        tags=["Bio"],
        class_detail=user_bio_detail_view,
        class_list=user_bio_list_view,
        schema=UserBioSchema,
        type_resource="user_bio",
        schema_in_patch=UserBioPatchSchema,
        schema_in_post=UserBioInSchema,
        model=UserBio,
        engine=DBORMType.sqlalchemy,
    )

    app_plain.include_router(router, prefix="")

    return app_plain


@async_fixture()
async def client(app: FastAPI) -> AsyncClient:
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


# app ⬆️


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
        assert user_data["id"] == str(user.id)
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
    assert response_data["data"]["id"] == str(user_1.id)
    assert response_data["data"]["type"] == "user"
    assert "included" in response_data, response_data
    included_bio = response_data["included"][0]
    assert included_bio["id"] == str(user_1_bio.id)
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
        assert user_data["id"] == str(user.id)
        assert user_data["type"] == "user"

    assert "included" in response_data, response_data
    included_bio = response_data["included"][0]
    assert included_bio["id"] == str(user_1_bio.id)
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
        assert user_data["id"] == str(user.id)
        assert user_data["type"] == "user"

    for post_data, post in zip(posts_data, posts):
        assert post_data["id"] == str(post.id)
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
            "id": str(user.id),
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

    included_data = {(data["type"], data["id"]): data for data in included}

    for user_data, (user, user_posts, expected_bio) in zip(
        users_data,
        [(user_1, user_1_posts, user_1_bio), (user_2, user_2_posts, None)],
    ):
        assert user_data["id"] == str(user.id)
        assert user_data["type"] == "user"
        user_relationships = user_data["relationships"]
        posts_relation = user_relationships["posts"]["data"]
        assert len(posts_relation) == len(user_posts)
        for post_relation in posts_relation:
            assert (post_relation["type"], post_relation["id"]) in included_data

        bio_relation = user_relationships["bio"]["data"]
        if bio_relation is None:
            # bio may be not present
            assert expected_bio is None
            continue

        assert bio_relation == {
            "id": str(user_1_bio.id),
            "type": "user_bio",
        }

    # ! assert posts have expected post comments
    for posts, comments, comment_author in [
        ([user_1_post_for_comments], [user_2_comment_for_one_u1_post], user_2),
        (user_2_posts, user_1_comments_for_u2_posts, user_1),
    ]:
        for post, post_comment in zip(posts, comments):
            post_data = included_data[("post", str(post.id))]
            post_relationships = post_data["relationships"]
            assert "comments" in post_relationships
            post_comments_relation = post_relationships["comments"]["data"]
            post_comments = [post_comment]
            assert len(post_comments_relation) == len(post_comments)
            for comment_relation_data, comment in zip(post_comments_relation, post_comments):
                assert comment_relation_data == {
                    "id": str(comment.id),
                    "type": "post_comment",
                }

                comment_data = included_data[("post_comment", str(comment.id))]
                assert comment_data["relationships"]["author"]["data"] == {
                    "id": str(comment_author.id),
                    "type": "user",
                }
                assert ("user", str(comment_author.id)) in included_data
