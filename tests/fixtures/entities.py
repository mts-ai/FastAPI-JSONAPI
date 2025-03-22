from textwrap import dedent
from typing import Awaitable, Callable, Optional

import pytest
from pytest_asyncio import fixture as async_fixture
from sqlalchemy.ext.asyncio import AsyncSession

from examples.api_for_sqlalchemy.models import (
    AgeRating,
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
from tests.common import is_postgres_tests
from tests.fixtures.models import Task
from tests.misc.utils import fake


def build_user(**fields) -> User:
    fake_fields = {
        "name": fake.name(),
        "email": fake.email(),
        "age": fake.pyint(),
    }
    return User(**(fake_fields | fields))


def build_computer(**fields) -> Computer:
    fields = {
        "name": fake.name(),
        **fields,
    }
    return Computer(**fields)


def build_user_bio(user: User, **fields) -> UserBio:
    return UserBio(user=user, **fields)


async def create_user(async_session: AsyncSession, **fields) -> User:
    user = build_user(**fields)
    async_session.add(user)
    await async_session.commit()
    return user


async def create_user_bio(async_session: AsyncSession, user: User, **fields) -> UserBio:
    user_bio = build_user_bio(user=user, **fields)
    async_session.add(user_bio)
    await async_session.commit()
    return user_bio


async def create_computer(async_session: AsyncSession, **fields) -> Computer:
    computer = build_computer(**fields)
    async_session.add(computer)
    await async_session.commit()
    return computer


@async_fixture()
async def user_1(async_session: AsyncSession):
    user = build_user()
    async_session.add(user)
    await async_session.commit()

    yield user

    await async_session.delete(user)
    await async_session.commit()


@async_fixture()
async def user_2(async_session: AsyncSession):
    user = build_user()
    async_session.add(user)
    await async_session.commit()

    yield user

    await async_session.delete(user)
    await async_session.commit()


@async_fixture()
async def user_3(async_session: AsyncSession):
    user = build_user()
    async_session.add(user)
    await async_session.commit()

    yield user

    await async_session.delete(user)
    await async_session.commit()


@async_fixture()
async def user_1_bio(async_session: AsyncSession, user_1: User) -> UserBio:
    return await create_user_bio(
        async_session=async_session,
        user=user_1,
        birth_city="Moscow",
        favourite_movies="Django, Alien",
    )


@async_fixture()
async def user_2_bio(async_session: AsyncSession, user_2: User) -> UserBio:
    return await create_user_bio(
        async_session=async_session,
        user=user_2,
        birth_city="Snezhnogorsk",
        favourite_movies="A Beautiful Mind, Rocky",
    )


def build_post(user: User, **fields) -> Post:
    fields = {
        "title": fake.name(),
        "body": fake.sentence(),
        **fields,
    }
    return Post(user=user, **fields)


async def create_post(async_session: AsyncSession, user: User, **fields) -> Post:
    post = build_post(user, **fields)
    async_session.add(post)
    await async_session.commit()
    return post


@async_fixture()
async def user_1_posts(async_session: AsyncSession, user_1: User) -> list[Post]:
    posts = [
        Post(
            title=f"post_u1_{i}",
            user=user_1,
            body=fake.sentence(),
        )
        for i in range(1, 4)
    ]
    async_session.add_all(posts)
    await async_session.commit()
    return posts


@async_fixture()
async def user_1_post(async_session: AsyncSession, user_1: User):
    post = Post(
        title="post_for_u1",
        user=user_1,
    )
    async_session.add(post)
    await async_session.commit()

    yield post

    await async_session.delete(post)
    await async_session.commit()


@async_fixture()
async def user_2_posts(async_session: AsyncSession, user_2: User) -> list[Post]:
    posts = [
        Post(
            title=f"post_u2_{i}",
            user=user_2,
            body=fake.sentence(),
        )
        for i in range(1, 5)
    ]
    async_session.add_all(posts)
    await async_session.commit()
    return posts


@async_fixture()
async def user_1_comments_for_u2_posts(async_session: AsyncSession, user_1, user_2_posts):
    post_comments = [
        PostComment(
            text=f"comment_{i}_for_post_{post.id}",
            post=post,
            user=user_1,
        )
        for i, post in enumerate(user_2_posts, start=1)
    ]
    async_session.add_all(post_comments)
    await async_session.commit()

    yield post_comments

    for comment in post_comments:
        await async_session.delete(comment)
    await async_session.commit()


@pytest.fixture
def user_1_post_for_comments(user_1_posts: list[Post]) -> Post:
    return user_1_posts[0]


@async_fixture()
async def computer_1(async_session: AsyncSession):
    computer = Computer(
        name="Halo",
    )
    async_session.add(computer)
    await async_session.commit()

    yield computer

    await async_session.delete(computer)
    await async_session.commit()


@async_fixture()
async def computer_2(async_session: AsyncSession):
    computer = Computer(
        name="Nestor",
    )
    async_session.add(computer)
    await async_session.commit()

    yield computer

    await async_session.delete(computer)
    await async_session.commit()


@async_fixture()
async def computer_factory(async_session: AsyncSession) -> Callable[[Optional[str]], Awaitable[Computer]]:
    async def factory(name: Optional[str] = None) -> Computer:
        computer = Computer(name=name or fake.word())
        async_session.add(computer)
        await async_session.commit()
        return computer

    return factory


def build_post_comment(user: User, post: Post, **fields) -> PostComment:
    fields = {
        "text": fake.sentence(),
        **fields,
    }
    return PostComment(
        user=user,
        post=post,
        **fields,
    )


async def create_post_comment(
    async_session: AsyncSession,
    user: User,
    post: Post,
    **fields,
) -> PostComment:
    post_comment = build_post_comment(user=user, post=post, **fields)
    async_session.add(post_comment)
    await async_session.commit()
    return post_comment


@async_fixture()
async def user_2_comment_for_one_u1_post(async_session: AsyncSession, user_2, user_1_post_for_comments):
    post_comment = PostComment(
        text=f"one_comment_from_u2_for_post_{user_1_post_for_comments.id}",
        post=user_1_post_for_comments,
        user=user_2,
    )
    async_session.add(post_comment)
    await async_session.commit()

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

    yield assoc

    await async_session.delete(assoc)
    await async_session.commit()


def build_task(**fields):
    return Task(**fields)


async def create_task(async_session: AsyncSession, **fields):
    task = build_task(**fields)
    async_session.add(task)
    await async_session.commit()
    return task


@async_fixture()
async def task_1(
    async_session: AsyncSession,
):
    fields = {
        "task_ids_list_json": [1, 2, 3],
        "task_ids_dict_json": {"completed": [1, 2, 3], "count": 1, "is_complete": True},
    }
    if is_postgres_tests():
        fields.update(
            {
                "task_ids_list_jsonb": ["a", "b", "c"],
                "task_ids_dict_jsonb": {"completed": ["a", "b", "c"], "count": 2, "is_complete": True},
            },
        )
    yield await create_task(async_session, **fields)


@async_fixture()
async def task_2(
    async_session: AsyncSession,
):
    fields = {
        "task_ids_list_json": [4, 5, 6],
        "task_ids_dict_json": {"completed": [4, 5, 6], "count": 3, "is_complete": False},
    }
    if is_postgres_tests():
        fields.update(
            {
                "task_ids_list_jsonb": ["d", "e", "f"],
                "task_ids_dict_jsonb": {"completed": ["d", "e", "f"], "count": 4, "is_complete": False},
            },
        )
    yield await create_task(async_session, **fields)


def build_workplace(**fields):
    return Workplace(**fields)


def build_age_rating(name: str, description: str) -> AgeRating:
    return AgeRating(
        name=name,
        description=description,
    )


async def create_workplace(async_session: AsyncSession, **fields):
    workplace = build_workplace(**fields)
    async_session.add(workplace)
    await async_session.commit()
    return workplace


async def create_age_rating(async_session: AsyncSession, **fields):
    age_rating = build_age_rating(**fields)
    async_session.add(age_rating)
    await async_session.commit()
    return age_rating


@async_fixture()
async def workplace_1(
    async_session: AsyncSession,
):
    yield await create_workplace(async_session, name="workplace_1")


@async_fixture()
async def workplace_2(
    async_session: AsyncSession,
):
    yield await create_workplace(async_session, name="workplace_2")


@async_fixture()
async def age_rating_g(async_session: AsyncSession) -> AgeRating:
    return await create_age_rating(
        async_session=async_session,
        name="G",
        description=dedent(
            """G – General Audiences

        All ages admitted.
        Nothing that would offend parents for viewing by children.
        """,
        ),
    )
