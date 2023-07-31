from typing import List

from pytest import fixture  # noqa
from pytest_asyncio import fixture as async_fixture
from sqlalchemy.ext.asyncio import AsyncSession

from tests.misc.utils import fake
from tests.models import (
    Child,
    Computer,
    Parent,
    ParentToChildAssociation,
    Post,
    PostComment,
    User,
    UserBio,
    Workplace,
)


def build_user(**fields) -> User:
    fake_fields = {
        "name": fake.name(),
        "email": fake.email(),
        "age": fake.pyint(),
    }
    return User(**(fake_fields | fields))


async def create_user(async_session: AsyncSession, **fields):
    user = build_user(**fields)
    async_session.add(user)
    await async_session.commit()

    return user


@async_fixture()
async def user_1(async_session: AsyncSession):
    user = build_user()
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    yield user
    await async_session.delete(user)
    await async_session.commit()


@async_fixture()
async def user_2(async_session: AsyncSession):
    user = build_user()
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    yield user
    await async_session.delete(user)
    await async_session.commit()


@async_fixture()
async def user_3(async_session: AsyncSession):
    user = build_user()
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
    await async_session.commit()


@async_fixture
async def computer_2(async_session: AsyncSession):
    computer = Computer(name="Nestor")

    async_session.add(computer)
    await async_session.commit()
    await async_session.refresh(computer)

    yield computer

    await async_session.delete(computer)
    await async_session.commit()


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


async def build_workplace(async_session: AsyncSession, **fields):
    workplace = Workplace(**fields)
    async_session.add(workplace)

    await async_session.commit()

    return workplace


@async_fixture()
async def workplace_1(
    async_session: AsyncSession,
):
    yield await build_workplace(async_session, name="workplace_1")


@async_fixture()
async def workplace_2(
    async_session: AsyncSession,
):
    yield await build_workplace(async_session, name="workplace_2")
