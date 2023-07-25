from typing import List

from fastapi import APIRouter, Depends, FastAPI
from httpx import AsyncClient
from pytest import fixture  # noqa
from pytest_asyncio import fixture as async_fixture
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from fastapi_jsonapi import RoutersJSONAPI
from fastapi_jsonapi.exceptions.handlers import register_exception_handlers
from fastapi_jsonapi.misc.sqla.generics.base import (
    DetailViewBaseGeneric as DetailViewBaseGenericHelper,
)
from fastapi_jsonapi.misc.sqla.generics.base import (
    ListViewBaseGeneric as ListViewBaseGenericHelper,
)
from tests.models import (
    Base,
    Child,
    Computer,
    Parent,
    ParentToChildAssociation,
    Post,
    PostComment,
    User,
    UserBio,
)
from tests.schemas import (
    ChildInSchema,
    ChildPatchSchema,
    ChildSchema,
    ParentPatchSchema,
    ParentSchema,
    PostInSchema,
    PostPatchSchema,
    PostSchema,
    UserBioSchema,
    UserInSchema,
    UserPatchSchema,
    UserSchema,
)


@fixture(scope="session")
def sqla_uri():
    return "sqlite+aiosqlite:///tests/db.sqlite3"
    # return "sqlite+aiosqlite:///:memory:"


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


@fixture(scope="class")
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


@fixture()
def user_1_post_for_comments(user_1_posts: List[Post]) -> Post:
    return user_1_posts[0]


@async_fixture
async def computer_1(async_session: AsyncSession):
    computer = Computer(name="Halo")

    async_session.add(computer)
    await async_session.commit()
    await async_session.refresh(computer)

    yield computer

    await async_session.delete(computer)


@async_fixture
async def computer_2(async_session: AsyncSession):
    computer = Computer(name="Nestor")

    async_session.add(computer)
    await async_session.commit()
    await async_session.refresh(computer)

    yield computer

    await async_session.delete(computer)


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


@fixture(scope="class")
def detail_view_base_generic(async_session_dependency):
    class DetailViewBaseGeneric(DetailViewBaseGenericHelper):
        async def init_dependencies(self, session: AsyncSession = Depends(async_session_dependency)):
            self.session = session

    return DetailViewBaseGeneric


@fixture(scope="class")
def list_view_base_generic(async_session_dependency):
    class ListViewBaseGeneric(ListViewBaseGenericHelper):
        async def init_dependencies(self, session: AsyncSession = Depends(async_session_dependency)):
            self.session = session

    return ListViewBaseGeneric


@fixture(scope="class")
def list_view_base_generic_helper_for_sqla(async_session_dependency):
    class ListViewBaseGeneric(ListViewBaseGenericHelper):
        async def init_dependencies(self, session: AsyncSession = Depends(async_session_dependency)):
            self.session = session

    return ListViewBaseGeneric


# User ⬇️


@fixture(scope="class")
def user_detail_view(detail_view_base_generic):
    """
    :param detail_view_base_generic:
    :return:
    """

    class UserDetail(detail_view_base_generic):
        ...

    return UserDetail


@fixture(scope="class")
def user_list_view(list_view_base_generic_helper_for_sqla):
    """
    :param list_view_base_generic_helper_for_sqla:
    :return:
    """

    class UserList(list_view_base_generic_helper_for_sqla):
        ...

    return UserList


# User Bio ⬇️


@fixture(scope="class")
def user_bio_detail_view(detail_view_base_generic):
    """
    :param detail_view_base_generic:
    :return:
    """

    class UserBioDetail(detail_view_base_generic):
        ...

    return UserBioDetail


@fixture(scope="class")
def user_bio_list_view(list_view_base_generic):
    """
    :param list_view_base_generic:
    :return:
    """

    class UserBioList(list_view_base_generic):
        ...

    return UserBioList


# Post ⬇️


@fixture(scope="class")
def post_detail_view(detail_view_base_generic):
    """
    :param detail_view_base_generic:
    :return:
    """

    class PostDetail(detail_view_base_generic):
        ...

    return PostDetail


@fixture(scope="class")
def post_list_view(list_view_base_generic):
    """
    :param list_view_base_generic:
    :return:
    """

    class PostList(list_view_base_generic):
        ...

    return PostList


# Parent ⬇️


@fixture(scope="class")
def parent_detail_view(detail_view_base_generic):
    """
    :param detail_view_base_generic:
    :return:
    """

    class ParentDetail(detail_view_base_generic):
        ...

    return ParentDetail


@fixture(scope="class")
def parent_list_view(list_view_base_generic):
    """
    :param list_view_base_generic:
    :return:
    """

    class ParentList(list_view_base_generic):
        ...

    return ParentList


# Child ⬇️


@fixture(scope="class")
def child_detail_view(detail_view_base_generic):
    """
    :param detail_view_base_generic:
    :return:
    """

    class ChildDetail(detail_view_base_generic):
        ...

    return ChildDetail


@fixture(scope="class")
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


@fixture()
def app_max_include_depth():
    return 5


@fixture()
def app_plain(app_max_include_depth) -> FastAPI:
    app = FastAPI(
        title="FastAPI and SQLAlchemy",
        debug=True,
        openapi_url="/openapi.json",
        docs_url="/docs",
    )
    app.config = {"MAX_INCLUDE_DEPTH": app_max_include_depth}
    return app


# Routing ⬇️


@fixture()
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


@async_fixture()
async def client(app: FastAPI) -> AsyncClient:
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
