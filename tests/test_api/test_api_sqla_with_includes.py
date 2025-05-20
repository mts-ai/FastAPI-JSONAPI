import logging
from collections import defaultdict
from datetime import datetime, timezone
from itertools import chain
from typing import Annotated, Literal
from unittest import mock
from unittest.mock import call
from uuid import UUID, uuid4

import orjson as json
import pytest
from fastapi import FastAPI, status
from fastapi.datastructures import QueryParams
from httpx import AsyncClient
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from examples.api_for_sqlalchemy.models import Computer, Post, PostComment, User, UserBio, Workplace
from examples.api_for_sqlalchemy.schemas import (
    CustomUserAttributesSchema,
    PostAttributesBaseSchema,
    PostCommentAttributesBaseSchema,
    UserAttributesBaseSchema,
    UserBioAttributesBaseSchema,
    UserInSchemaAllowIdOnPost,
    UserPatchSchema,
    UserSchema,
)
from fastapi_jsonapi.data_layers.sqla import query_building as query_building_module
from fastapi_jsonapi.types_metadata import ClientCanSetId
from fastapi_jsonapi.types_metadata.custom_filter_sql import sql_filter_lower_equals
from fastapi_jsonapi.types_metadata.custom_sort_sql import sql_register_free_sort
from tests.common import is_postgres_tests
from tests.fixtures.app import build_alphabet_app, build_app_custom
from tests.fixtures.entities import (
    create_computer,
    create_post,
    create_post_comment,
    create_user,
    create_user_bio,
    create_workplace,
)
from tests.fixtures.models import (
    Alpha,
    Beta,
    CascadeCase,
    ContainsTimestamp,
    CustomUUIDItem,
    Delta,
    Gamma,
    SelfRelationship,
)
from tests.fixtures.schemas import CascadeCaseSchema, CustomUUIDItemAttributesSchema, SelfRelationshipAttributesSchema
from tests.misc.utils import fake

logging.basicConfig(level=logging.DEBUG)


def association_key(data: dict):
    return data["type"], data["id"]


async def test_root(client: AsyncClient):
    response = await client.get("/docs")
    assert response.status_code == status.HTTP_200_OK


async def test_get_users(app: FastAPI, client: AsyncClient, user_1: User, user_2: User):
    url = app.url_path_for("get_user_list")
    response = await client.get(url)
    assert response.status_code == status.HTTP_200_OK, response.text
    response_data = response.json()
    assert "data" in response_data, response_data
    users_data = response_data["data"]
    users = [user_1, user_2]
    assert len(users_data) == len(users)
    for user_data, user in zip(users_data, users):
        assert user_data["id"] == f"{user.id}"
        assert user_data["type"] == "user"


async def test_get_user_with_bio_relation(
    app: FastAPI,
    client: AsyncClient,
    user_1: User,
    user_1_bio: UserBio,
):
    url = app.url_path_for("get_user_detail", obj_id=user_1.id)
    url = f"{url}?include=bio"
    response = await client.get(url)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert "data" in response_data, response_data
    assert response_data["data"]["id"] == f"{user_1.id}"
    assert response_data["data"]["type"] == "user"
    assert "included" in response_data, response_data
    included_bio = response_data["included"][0]
    assert included_bio["id"] == f"{user_1_bio.id}"
    assert included_bio["type"] == "user_bio"


async def test_get_users_with_bio_relation(
    app: FastAPI,
    client: AsyncClient,
    user_1: User,
    user_2: User,
    user_1_bio: UserBio,
):
    url = app.url_path_for("get_user_list")
    url = f"{url}?include=bio"
    response = await client.get(url)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert "data" in response_data, response_data
    users_data = response_data["data"]
    users = [user_1, user_2]
    assert len(users_data) == len(users)
    for user_data, user in zip(users_data, users):
        assert user_data["id"] == f"{user.id}"
        assert user_data["type"] == "user"

    assert "included" in response_data, response_data
    included_bio = response_data["included"][0]
    assert included_bio["id"] == f"{user_1_bio.id}"
    assert included_bio["type"] == "user_bio"


class TestGetUsersList:
    async def test_get_users_paginated(
        self,
        app: FastAPI,
        client: AsyncClient,
        user_1: User,
        user_2: User,
    ):
        url = app.url_path_for("get_user_list")
        url = f"{url}?page[size]=1&sort=id"
        response = await client.get(url)
        user = user_1 if user_1.id < user_2.id else user_2

        assert response.status_code == status.HTTP_200_OK, response.text
        response_data = response.json()
        expected_data = [
            {
                "attributes": UserAttributesBaseSchema.model_validate(user).model_dump(),
                "id": f"{user.id}",
                "type": "user",
            },
        ]
        assert "data" in response_data
        assert response_data["data"] == expected_data

    @pytest.mark.parametrize(
        ("fields", "expected_include"),
        [
            pytest.param(
                [
                    ("fields[user]", "name,age"),
                ],
                {"name", "age"},
            ),
            pytest.param(
                [
                    ("fields[user]", "name,age"),
                    ("fields[user]", "email"),
                ],
                {"name", "age", "email"},
            ),
        ],
    )
    async def test_select_custom_fields(
        self,
        app: FastAPI,
        client: AsyncClient,
        user_1: User,
        user_2: User,
        fields: list[tuple[str, str]],
        expected_include: set[str],
    ):
        url = app.url_path_for("get_user_list")
        user_1, user_2 = sorted((user_1, user_2), key=lambda x: x.id)

        params = QueryParams(fields)
        response = await client.get(url, params=f"{params}")

        assert response.status_code == status.HTTP_200_OK, response.text
        response_data = response.json()

        assert response_data == {
            "data": [
                {
                    "attributes": UserAttributesBaseSchema.model_validate(user_1).model_dump(include=expected_include),
                    "id": f"{user_1.id}",
                    "type": "user",
                },
                {
                    "attributes": UserAttributesBaseSchema.model_validate(user_2).model_dump(include=expected_include),
                    "id": f"{user_2.id}",
                    "type": "user",
                },
            ],
            "jsonapi": {"version": "1.0"},
            "meta": {"count": 2, "totalPages": 1},
        }

    async def test_select_custom_fields_with_includes(
        self,
        app: FastAPI,
        async_session: AsyncSession,
        client: AsyncClient,
        user_1: User,
        user_2: User,
    ):
        url = app.url_path_for("get_user_list")
        user_1, user_2 = sorted((user_1, user_2), key=lambda x: x.id)

        user_2_post = await create_post(async_session, user_2)
        user_1_post = await create_post(async_session, user_1)

        user_1_comment = await create_post_comment(async_session, user_1, user_2_post)
        user_2_comment = await create_post_comment(async_session, user_2, user_1_post)

        queried_user_fields = "name"
        queried_post_fields = "title"

        params = QueryParams(
            [
                ("fields[user]", queried_user_fields),
                ("fields[post]", queried_post_fields),
                # empty str means ignore all fields
                ("fields[post_comment]", ""),
                ("include", "posts,posts.comments"),
                ("sort", "id"),
            ],
        )
        response = await client.get(url, params=f"{params}")

        assert response.status_code == status.HTTP_200_OK, response.text
        response_data = response.json()
        response_data["included"] = sorted(response_data["included"], key=lambda x: (x["type"], x["id"]))

        assert response_data == {
            "data": [
                {
                    "attributes": UserAttributesBaseSchema.model_validate(user_1).model_dump(
                        include=set(queried_user_fields.split(",")),
                    ),
                    "relationships": {
                        "posts": {
                            "data": [
                                {
                                    "id": f"{user_1_post.id}",
                                    "type": "post",
                                },
                            ],
                        },
                    },
                    "id": f"{user_1.id}",
                    "type": "user",
                },
                {
                    "attributes": UserAttributesBaseSchema.model_validate(user_2).model_dump(
                        include=set(queried_user_fields.split(",")),
                    ),
                    "relationships": {
                        "posts": {
                            "data": [
                                {
                                    "id": f"{user_2_post.id}",
                                    "type": "post",
                                },
                            ],
                        },
                    },
                    "id": f"{user_2.id}",
                    "type": "user",
                },
            ],
            "jsonapi": {"version": "1.0"},
            "meta": {"count": 2, "totalPages": 1},
            "included": sorted(
                [
                    {
                        "attributes": PostAttributesBaseSchema.model_validate(user_2_post).model_dump(
                            include=set(queried_post_fields.split(",")),
                        ),
                        "id": f"{user_2_post.id}",
                        "relationships": {
                            "comments": {
                                "data": [
                                    {
                                        "id": f"{user_1_comment.id}",
                                        "type": "post_comment",
                                    },
                                ],
                            },
                        },
                        "type": "post",
                    },
                    {
                        "attributes": PostAttributesBaseSchema.model_validate(user_1_post).model_dump(
                            include=set(queried_post_fields.split(",")),
                        ),
                        "id": f"{user_1_post.id}",
                        "relationships": {
                            "comments": {
                                "data": [
                                    {
                                        "id": f"{user_2_comment.id}",
                                        "type": "post_comment",
                                    },
                                ],
                            },
                        },
                        "type": "post",
                    },
                    {
                        "attributes": {},
                        "id": f"{user_1_comment.id}",
                        "type": "post_comment",
                    },
                    {
                        "attributes": {},
                        "id": f"{user_2_comment.id}",
                        "type": "post_comment",
                    },
                ],
                key=lambda x: (x["type"], x["id"]),
            ),
        }

    async def test_select_custom_fields_with_includes_other_direction(
        self,
        app: FastAPI,
        async_session: AsyncSession,
        client: AsyncClient,
        user_1: User,
        user_2: User,
    ):
        url = app.url_path_for("get_post_list")
        user_1, user_2 = sorted((user_1, user_2), key=lambda x: x.id)

        user_2_post = await create_post(async_session, user_2)
        user_1_post = await create_post(async_session, user_1)

        queried_user_fields = "name"
        queried_post_fields = "title"

        params = QueryParams(
            [
                ("fields[user]", queried_user_fields),
                ("fields[post]", queried_post_fields),
                ("include", "user"),
            ],
        )
        response = await client.get(url, params=f"{params}")

        assert response.status_code == status.HTTP_200_OK, response.text
        response_data = response.json()
        response_data["data"] = sorted(response_data["data"], key=lambda x: (x["type"], x["id"]))
        response_data["included"] = sorted(response_data["included"], key=lambda x: (x["type"], x["id"]))

        assert response_data == {
            "data": [
                {
                    "id": f"{user_2_post.id}",
                    "type": "post",
                    "attributes": PostAttributesBaseSchema.model_validate(user_2_post).model_dump(
                        include=set(queried_post_fields.split(",")),
                    ),
                    "relationships": {"user": {"data": {"id": f"{user_2.id}", "type": "user"}}},
                },
                {
                    "id": f"{user_1_post.id}",
                    "type": "post",
                    "attributes": PostAttributesBaseSchema.model_validate(user_1_post).model_dump(
                        include=set(queried_post_fields.split(",")),
                    ),
                    "relationships": {"user": {"data": {"id": f"{user_1.id}", "type": "user"}}},
                },
            ],
            "jsonapi": {"version": "1.0"},
            "meta": {"count": 2, "totalPages": 1},
            "included": sorted(
                [
                    {
                        "id": f"{user_1.id}",
                        "type": "user",
                        "attributes": UserAttributesBaseSchema.model_validate(user_1).model_dump(
                            include=set(queried_user_fields.split(",")),
                        ),
                    },
                    {
                        "id": f"{user_2.id}",
                        "type": "user",
                        "attributes": UserAttributesBaseSchema.model_validate(user_2).model_dump(
                            include=set(queried_user_fields.split(",")),
                        ),
                    },
                ],
                key=lambda x: (x["type"], x["id"]),
            ),
        }

    async def test_select_custom_fields_for_includes_without_requesting_includes(
        self,
        app: FastAPI,
        client: AsyncClient,
        user_1: User,
    ):
        url = app.url_path_for("get_user_list")

        params = QueryParams([("fields[post]", "title")])
        response = await client.get(url, params=f"{params}")

        assert response.status_code == status.HTTP_200_OK, response.text
        response_data = response.json()

        assert response_data == {
            "data": [
                {
                    "attributes": UserAttributesBaseSchema.model_validate(user_1).model_dump(),
                    "id": f"{user_1.id}",
                    "type": "user",
                },
            ],
            "jsonapi": {"version": "1.0"},
            "meta": {"count": 1, "totalPages": 1},
        }


class TestCreatePostAndComments:
    async def test_get_posts_with_users(
        self,
        app: FastAPI,
        client: AsyncClient,
        user_1: User,
        user_2: User,
        user_1_posts: list[Post],
        user_2_posts: list[Post],
    ):
        call(
            base_name="UserSchema",
            schema=UserSchema,
            includes=["posts"],
            non_optional_relationships=False,
            on_optional_relationships=False,
        )
        url = app.url_path_for("get_post_list")
        url = f"{url}?include=user"
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
            assert user_data["id"] == f"{user.id}"
            assert user_data["type"] == "user"

        for post_data, post in zip(posts_data, posts):
            assert post_data["id"] == f"{post.id}"
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

            for post_data in posts_data:
                user_relation = post_data["relationships"]["user"]
                assert user_relation["data"] == {
                    "id": f"{user.id}",
                    "type": "user",
                }

    async def test_create_post_for_user(
        self,
        app: FastAPI,
        client: AsyncClient,
        user_1: User,
    ):
        url = app.url_path_for("get_post_list")
        url = f"{url}?include=user"
        post_attributes = PostAttributesBaseSchema(
            title=fake.name(),
            body=fake.sentence(),
        ).model_dump()
        post_create = {
            "data": {
                "attributes": post_attributes,
                "relationships": {
                    "user": {
                        "data": {
                            "type": "user",
                            "id": f"{user_1.id}",
                        },
                    },
                },
            },
        }
        response = await client.post(url, json=post_create)
        assert response.status_code == status.HTTP_201_CREATED, response.text
        response_data = response.json()
        post_data: dict = response_data["data"]
        assert post_data.pop("id")
        assert post_data == {
            "type": "post",
            "attributes": post_attributes,
            "relationships": {
                "user": {
                    "data": {
                        "type": "user",
                        "id": f"{user_1.id}",
                    },
                },
            },
        }
        included = response_data["included"]
        assert included == [
            {
                "id": f"{user_1.id}",
                "type": "user",
                "attributes": UserAttributesBaseSchema.model_validate(user_1).model_dump(exclude_unset=True),
            },
        ]

    async def test_create_comments_for_post(
        self,
        app: FastAPI,
        client: AsyncClient,
        user_1: User,
        user_2: User,
        user_1_post: Post,
    ):
        url = app.url_path_for("get_post_comment_list")
        url = f"{url}?include=user,post,post.user"
        comment_attributes = PostCommentAttributesBaseSchema(
            text=fake.sentence(),
        ).model_dump()
        comment_create = {
            "data": {
                "attributes": comment_attributes,
                "relationships": {
                    "post": {
                        "data": {
                            "type": "post",
                            "id": f"{user_1_post.id}",
                        },
                    },
                    "user": {
                        "data": {
                            "type": "user",
                            "id": f"{user_2.id}",
                        },
                    },
                },
            },
        }
        response = await client.post(url, json=comment_create)
        assert response.status_code == status.HTTP_201_CREATED, response.text
        response_data = response.json()
        comment_data: dict = response_data["data"]
        comment_id = comment_data.pop("id")
        assert comment_id
        assert comment_data == {
            "type": "post_comment",
            "attributes": comment_attributes,
            "relationships": {
                "post": {
                    "data": {
                        "type": "post",
                        "id": f"{user_1_post.id}",
                    },
                },
                "user": {
                    "data": {
                        "type": "user",
                        "id": f"{user_2.id}",
                    },
                },
            },
        }
        included = response_data["included"]
        assert included == [
            {
                "type": "post",
                "id": f"{user_1_post.id}",
                "attributes": PostAttributesBaseSchema.model_validate(user_1_post).model_dump(),
                "relationships": {
                    "user": {
                        "data": {
                            "id": f"{user_1.id}",
                            "type": "user",
                        },
                    },
                },
            },
            {
                "type": "user",
                "id": f"{user_1.id}",
                "attributes": UserAttributesBaseSchema.model_validate(user_1).model_dump(),
            },
            {
                "type": "user",
                "id": f"{user_2.id}",
                "attributes": UserAttributesBaseSchema.model_validate(user_2).model_dump(),
            },
        ]

    async def test_create_comment_error_no_relationship(
        self,
        app: FastAPI,
        client: AsyncClient,
        user_1_post: Post,
    ):
        """
        Check schema is built properly

        :param app
        :param client:
        :param user_1_post:
        :return:
        """
        url = app.url_path_for("get_post_comment_list")
        comment_attributes = PostCommentAttributesBaseSchema(
            text=fake.sentence(),
        ).model_dump()
        comment_create = {
            "data": {
                "attributes": comment_attributes,
                "relationships": {
                    "post": {
                        "data": {
                            "type": "post",
                            "id": f"{user_1_post.id}",
                        },
                    },
                    # don"t pass "user"
                },
            },
        }
        response = await client.post(url, json=comment_create)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, response.text
        response_data = response.json()
        detail, *_ = response_data["detail"]
        assert detail["loc"] == ["body", "data", "relationships", "user"]
        assert detail["msg"] == "Field required"

    async def test_create_comment_error_no_relationships_content(
        self,
        app: FastAPI,
        client: AsyncClient,
    ):
        url = app.url_path_for("get_post_comment_list")
        comment_attributes = PostCommentAttributesBaseSchema(
            text=fake.sentence(),
        ).model_dump()
        comment_create = {
            "data": {
                "attributes": comment_attributes,
                "relationships": {
                    # don"t pass "post"
                    # don"t pass "user"
                },
            },
        }
        response = await client.post(url, json=comment_create)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, response.text
        response_data = response.json()
        detail_1, detail_2 = response_data["detail"]
        assert detail_1["loc"] == ["body", "data", "relationships", "post"]
        assert detail_1["msg"] == "Field required"
        assert detail_2["loc"] == ["body", "data", "relationships", "user"]
        assert detail_2["msg"] == "Field required"

    async def test_create_comment_error_no_relationships_field(
        self,
        app: FastAPI,
        client: AsyncClient,
    ):
        url = app.url_path_for("get_post_comment_list")
        comment_attributes = PostCommentAttributesBaseSchema(
            text=fake.sentence(),
        ).model_dump()
        comment_create = {
            "data": {
                "attributes": comment_attributes,
                # don"t pass "relationships" at all
            },
        }
        response = await client.post(url, json=comment_create)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, response.text
        response_data = response.json()
        detail, *_ = response_data["detail"]
        assert detail["loc"] == ["body", "data", "relationships"]
        assert detail["msg"] == "Field required"


async def test_get_users_with_all_inner_relations(
    app: FastAPI,
    client: AsyncClient,
    user_1: User,
    user_2: User,
    user_1_bio: UserBio,
    user_1_posts,
    user_1_post_for_comments: Post,
    user_2_posts: list[Post],
    user_1_comments_for_u2_posts: list[PostComment],
    user_2_comment_for_one_u1_post: PostComment,
):
    """
    Checks 4 levels of includes

    Include:
    - bio
    - posts
    - posts.comments
    - posts.comments.user
    """
    url = app.url_path_for("get_user_list")
    url = f"{url}?include=bio,posts,posts.comments,posts.comments.user"
    response = await client.get(url)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert "data" in response_data, response_data

    users = [user_1, user_2]
    users_data = response_data["data"]
    assert len(users_data) == len(users)

    assert "included" in response_data, response_data
    included: list[dict] = response_data["included"]

    included_data = {association_key(data): data for data in included}

    for user_data, (user, user_posts, expected_bio) in zip(
        users_data,
        [(user_1, user_1_posts, user_1_bio), (user_2, user_2_posts, None)],
    ):
        assert user_data["id"] == f"{user.id}"
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
            "id": f"{user_1_bio.id}",
            "type": "user_bio",
        }

    # ! assert posts have expected post comments
    for posts, comments, comment_user in [
        ([user_1_post_for_comments], [user_2_comment_for_one_u1_post], user_2),
        (user_2_posts, user_1_comments_for_u2_posts, user_1),
    ]:
        for post, post_comment in zip(posts, comments):
            post_data = included_data[("post", f"{post.id}")]
            post_relationships = post_data["relationships"]
            assert "comments" in post_relationships
            post_comments_relation = post_relationships["comments"]["data"]
            post_comments = [post_comment]
            assert len(post_comments_relation) == len(post_comments)
            for comment_relation_data, comment in zip(post_comments_relation, post_comments):
                assert comment_relation_data == {
                    "id": f"{comment.id}",
                    "type": "post_comment",
                }

                comment_data = included_data[("post_comment", f"{comment.id}")]
                assert comment_data["relationships"]["user"]["data"] == {
                    "id": f"{comment_user.id}",
                    "type": "user",
                }
                assert ("user", f"{comment_user.id}") in included_data


async def test_many_to_many_load_inner_includes_to_parents(
    app: FastAPI,
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
    url = app.url_path_for("get_parent_list")
    url = f"{url}?include=children,children.child"
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
        assert parent_data["id"] == f"{parent.id}"
        assert parent_data["type"] == "parent"

        parent_relationships = parent_data["relationships"]
        parent_to_children_assocs = parent_relationships["children"]["data"]
        assert len(parent_to_children_assocs) == len(expected_assocs)
        for assoc_data, (assoc, child) in zip(parent_to_children_assocs, expected_assocs):
            assert assoc_data["id"] == f"{assoc.id}"
            assert assoc_data["type"] == "parent_child_association"
            assoc_key = association_key(assoc_data)
            assert assoc_key in included_data
            p_to_c_assoc_data = included_data[assoc_key]
            assert p_to_c_assoc_data["relationships"]["child"]["data"] == {
                "id": f"{child.id}",
                "type": "child",
            }
            assert p_to_c_assoc_data["attributes"]["extra_data"] == assoc.extra_data

    assert ("child", f"{child_4.id}") not in included_data


class TestGetUserDetail:
    def get_url(self, app: FastAPI, user_id: int) -> str:
        return app.url_path_for("get_user_detail", obj_id=user_id)

    async def test_select_custom_fields(
        self,
        app: FastAPI,
        client: AsyncClient,
        user_1: User,
    ):
        url = self.get_url(app, user_1.id)
        queried_user_fields = "name,age"
        params = QueryParams([("fields[user]", queried_user_fields)])
        response = await client.get(url, params=params)

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "data": {
                "attributes": UserAttributesBaseSchema.model_validate(user_1).model_dump(
                    include=set(queried_user_fields.split(",")),
                ),
                "id": f"{user_1.id}",
                "type": "user",
            },
            "jsonapi": {"version": "1.0"},
            "meta": None,
        }


class TestUserFetchRelationships:
    @staticmethod
    def get_url(
        app: FastAPI,
        user_id: int,
        relationship_name: str,
        many: bool = False,
    ) -> str:
        suffix = "list" if many else "detail"
        return app.url_path_for(f"fetch_user_{relationship_name}_{suffix}", obj_id=user_id)

    async def test_fetch_to_one_relationship(
        self,
        app: FastAPI,
        client: AsyncClient,
        user_1: User,
        user_1_bio: UserBio,
    ):
        url = self.get_url(app, user_1.id, "bio")

        response = await client.get(url)
        assert response.status_code == status.HTTP_200_OK, response.text
        assert response.json() == {
            "data": {
                "attributes": UserBioAttributesBaseSchema.from_orm(user_1_bio).model_dump(),
                "id": str(user_1_bio.id),
                "type": "user_bio",
            },
            "jsonapi": {"version": "1.0"},
            "meta": None,
        }

    async def test_fetch_to_one_relationship_with_include(
        self,
        app: FastAPI,
        client: AsyncClient,
        user_1: User,
        user_1_bio: UserBio,
    ):
        url = self.get_url(app, user_1.id, "bio")
        params = QueryParams([("include", "user")])

        response = await client.get(url, params=params)
        assert response.status_code == status.HTTP_200_OK, response.text
        assert response.json() == {
            "data": {
                "attributes": UserBioAttributesBaseSchema.from_orm(user_1_bio).model_dump(),
                "id": f"{user_1_bio.id}",
                "type": "user_bio",
                "relationships": {"user": {"data": {"id": f"{user_1.id}", "type": "user"}}},
            },
            "jsonapi": {"version": "1.0"},
            "meta": None,
            "included": [
                {
                    "attributes": UserAttributesBaseSchema.from_orm(user_1).model_dump(),
                    "id": f"{user_1.id}",
                    "type": "user",
                },
            ],
        }

    async def test_fetch_to_many_relationship(
        self,
        app: FastAPI,
        client: AsyncClient,
        user_1: User,
        user_1_posts: list[Post],
    ):
        url = self.get_url(app, user_1.id, "posts", many=True)

        response = await client.get(url)
        assert response.status_code == status.HTTP_200_OK, response.text
        assert response.json() == {
            "data": [
                {
                    "id": f"{post.id}",
                    "type": "post",
                    "attributes": PostAttributesBaseSchema.from_orm(post).model_dump(),
                }
                for post in sorted(user_1_posts, key=lambda post: post.id)
            ],
            "jsonapi": {"version": "1.0"},
            "meta": {"count": len(user_1_posts), "totalPages": 1},
        }

    async def test_fetch_to_many_relationship_with_include(
        self,
        app: FastAPI,
        client: AsyncClient,
        user_1: User,
        user_1_posts: list[Post],
    ):
        url = self.get_url(app, user_1.id, "posts", many=True)
        params = QueryParams([("include", "user")])

        response = await client.get(url, params=params)
        assert response.status_code == status.HTTP_200_OK, response.text
        assert response.json() == {
            "data": [
                {
                    "id": f"{post.id}",
                    "type": "post",
                    "attributes": PostAttributesBaseSchema.from_orm(post).model_dump(),
                    "relationships": {"user": {"data": {"id": f"{user_1.id}", "type": "user"}}},
                }
                for post in sorted(user_1_posts, key=lambda post: post.id)
            ],
            "jsonapi": {"version": "1.0"},
            "meta": {"count": len(user_1_posts), "totalPages": 1},
            "included": [
                {
                    "attributes": UserAttributesBaseSchema.from_orm(user_1).model_dump(),
                    "id": f"{user_1.id}",
                    "type": "user",
                },
            ],
        }


class TestUserWithPostsWithInnerIncludes:
    @pytest.mark.parametrize(
        (
            "include",
            "expected_relationships_inner_relations",
            "expected_users",
        ),
        [
            pytest.param(
                ["posts", "posts.user"],
                {"post": ["user"], "user": []},
                ["user_1"],
                id="case_0",
            ),
            pytest.param(
                ["posts", "posts.comments"],
                {"post": ["comments"], "post_comment": []},
                [],
                id="case_1",
            ),
            pytest.param(
                ["posts", "posts.user", "posts.comments"],
                {"post": ["user", "comments"], "user": [], "post_comment": []},
                ["user_1"],
                id="case_2",
            ),
            pytest.param(
                ["posts", "posts.user", "posts.comments", "posts.comments.user"],
                {"post": ["user", "comments"], "post_comment": ["user"], "user": []},
                ["user_1", "user_2"],
                id="case_3",
            ),
        ],
    )
    async def test_get_users_with_posts_and_inner_includes(
        self,
        app: FastAPI,
        client: AsyncClient,
        user_1: User,
        user_2: User,
        user_1_posts: list[PostComment],
        user_1_post_for_comments: Post,
        user_2_comment_for_one_u1_post: PostComment,
        include: list[str],
        expected_relationships_inner_relations: dict[str, list[str]],
        expected_users: list[str],
    ):
        """
        Check returned data

        Test if requesting `posts.user` and `posts.comments`
        returns posts with both `user` and `comments`
        """
        assert user_1_posts
        assert user_2_comment_for_one_u1_post.user_id == user_2.id
        include_param = ",".join(include)
        resource_type = "user"
        url = app.url_path_for(f"get_{resource_type}_list")
        url = f"{url}?filter[name]={user_1.name}&include={include_param}"
        response = await client.get(url)
        assert response.status_code == status.HTTP_200_OK, response.text
        response_json = response.json()

        result_data = response_json["data"]

        assert result_data == [
            {
                "id": f"{user_1.id}",
                "type": resource_type,
                "attributes": UserAttributesBaseSchema.model_validate(user_1).model_dump(),
                "relationships": {
                    "posts": {
                        "data": [
                            # relationship info
                            {"id": f"{p.id}", "type": "post"}
                            # for every post
                            for p in user_1_posts
                        ],
                    },
                },
            },
        ]
        included_data = response_json["included"]
        included_as_map = defaultdict(list)
        for included_ in included_data:
            included_as_map[included_["type"]].append(included_)

        for item_type, items in included_as_map.items():
            expected_relationships = expected_relationships_inner_relations[item_type]
            for item in items:
                relationships = set(item.get("relationships", {}))
                assert relationships.intersection(expected_relationships) == set(
                    expected_relationships,
                ), f"Expected relationships {expected_relationships} not found in {item_type} {item['id']}"

        expected_includes = self.prepare_expected_includes(
            user_1=user_1,
            user_2=user_2,
            user_1_posts=user_1_posts,
            user_2_comment_for_one_u1_post=user_2_comment_for_one_u1_post,
            expected_users=expected_users,
        )

        for item_type, includes_names in expected_relationships_inner_relations.items():
            items = expected_includes[item_type]
            have_to_be_present = set(includes_names)
            for item in items:  # type: dict
                item_relationships = item.get("relationships", {})
                for key in tuple(item_relationships.keys()):
                    if key not in have_to_be_present:
                        item_relationships.pop(key)
                if not item_relationships:
                    item.pop("relationships", None)

        for key in set(expected_includes).difference(expected_relationships_inner_relations):
            expected_includes.pop(key)

        assert dict(included_as_map) == expected_includes

    def prepare_expected_includes(
        self,
        user_1: User,
        user_2: User,
        user_1_posts: list[PostComment],
        user_2_comment_for_one_u1_post: PostComment,
        expected_users: list[str],
    ):
        data = {
            "post": [
                {
                    "id": f"{p.id}",
                    "type": "post",
                    "attributes": PostAttributesBaseSchema.model_validate(p).model_dump(),
                    "relationships": {
                        "user": {
                            "data": {
                                "id": f"{user_1.id}",
                                "type": "user",
                            },
                        },
                        "comments": {
                            "data": (
                                [
                                    {
                                        "id": f"{user_2_comment_for_one_u1_post.id}",
                                        "type": "post_comment",
                                    },
                                ]
                                if p.id == user_2_comment_for_one_u1_post.post_id
                                else []
                            ),
                        },
                    },
                }
                for p in user_1_posts
            ],
            "post_comment": [
                {
                    "id": f"{user_2_comment_for_one_u1_post.id}",
                    "type": "post_comment",
                    "attributes": PostCommentAttributesBaseSchema.model_validate(
                        user_2_comment_for_one_u1_post,
                    ).model_dump(),
                    "relationships": {
                        "user": {
                            "data": {
                                "id": f"{user_2.id}",
                                "type": "user",
                            },
                        },
                    },
                },
            ],
        }

        if not expected_users:
            return data

        users = {
            "user_1": {
                "id": f"{user_1.id}",
                "type": "user",
                "attributes": UserAttributesBaseSchema.model_validate(user_1).model_dump(),
            },
            "user_2": {
                "id": f"{user_2.id}",
                "type": "user",
                "attributes": UserAttributesBaseSchema.model_validate(user_2).model_dump(),
            },
        }
        data["user"] = [users[expected_user] for expected_user in expected_users]
        return data


async def test_method_not_allowed(app: FastAPI, client: AsyncClient):
    url = app.url_path_for("get_user_list")
    res = await client.put(url, json={})
    assert res.status_code == status.HTTP_405_METHOD_NOT_ALLOWED, res.status_code


async def test_get_list_view_generic(app: FastAPI, client: AsyncClient, user_1: User):
    url = app.url_path_for("get_user_list")
    res = await client.get(url)
    assert res
    assert res.status_code == status.HTTP_200_OK
    response_json = res.json()
    users_data = response_json["data"]
    assert len(users_data) == 1, users_data
    user_data = users_data[0]
    assert user_data["id"] == f"{user_1.id}"
    assert user_data["attributes"] == UserAttributesBaseSchema.model_validate(user_1).model_dump(exclude_none=True)


async def test_get_user_not_found(app: FastAPI, client: AsyncClient):
    fake_id = fake.pyint()
    url = app.url_path_for("get_user_detail", obj_id=fake_id)
    res = await client.get(url)

    assert res.json() == {
        "errors": [
            {
                "detail": f"Resource User `users.id = {fake_id}` not found",
                "title": "Resource not found.",
                "status_code": status.HTTP_404_NOT_FOUND,
                "meta": {"pointer": ""},
            },
        ],
    }


class TestCreateObjects:
    async def test_create_object(self, app: FastAPI, client: AsyncClient):
        create_user_body = {
            "data": {
                "attributes": UserAttributesBaseSchema(
                    name=fake.name(),
                    age=fake.pyint(),
                    email=fake.email(),
                ).model_dump(),
            },
        }
        url = app.url_path_for("get_user_list")
        res = await client.post(url, json=create_user_body)
        assert res.status_code == status.HTTP_201_CREATED, res.text
        response_data = res.json()
        assert "data" in response_data, response_data
        assert response_data["data"]["attributes"] == create_user_body["data"]["attributes"]

    async def test_create_object_with_relationship_and_fetch_include(
        self,
        app: FastAPI,
        client: AsyncClient,
        user_1: User,
    ):
        create_user_bio_body = {
            "data": {
                "attributes": UserBioAttributesBaseSchema(
                    birth_city=fake.word(),
                    favourite_movies=fake.sentence(),
                ).model_dump(),
                "relationships": {
                    "user": {
                        "data": {
                            "type": "user",
                            "id": f"{user_1.id}",
                        },
                    },
                },
            },
        }
        url = app.url_path_for("get_user_bio_list")
        url = f"{url}?include=user"
        res = await client.post(url, json=create_user_bio_body)
        assert res.status_code == status.HTTP_201_CREATED, res.text
        response_data = res.json()
        assert "data" in response_data, response_data
        assert response_data["data"]["attributes"] == create_user_bio_body["data"]["attributes"]
        included_data = response_data.get("included")
        assert included_data, response_data
        assert isinstance(included_data, list), included_data
        included_user = included_data[0]
        assert isinstance(included_user, dict), included_user
        assert included_user["type"] == "user"
        assert included_user["id"] == f"{user_1.id}"
        assert included_user["attributes"] == UserAttributesBaseSchema.model_validate(user_1).model_dump()

    async def test_create_object_with_to_many_relationship_and_fetch_include(
        self,
        app: FastAPI,
        client: AsyncClient,
        computer_1: Computer,
        computer_2: Computer,
    ):
        create_user_body = {
            "data": {
                "attributes": UserAttributesBaseSchema(
                    name=fake.name(),
                    age=fake.pyint(),
                    email=fake.email(),
                ).model_dump(),
                "relationships": {
                    "computers": {
                        "data": [
                            {
                                "id": f"{computer_1.id}",
                                "type": "computer",
                            },
                            {
                                "id": f"{computer_2.id}",
                                "type": "computer",
                            },
                        ],
                    },
                },
            },
        }
        url = app.url_path_for("get_user_list")
        url = f"{url}?include=computers"
        res = await client.post(url, json=create_user_body)
        assert res.status_code == status.HTTP_201_CREATED, res.text

        response_data = res.json()
        assert "data" in response_data
        assert response_data["data"].pop("id")
        assert response_data == {
            "data": {
                "attributes": create_user_body["data"]["attributes"],
                "relationships": {
                    "computers": {
                        "data": [
                            {
                                "id": f"{computer_1.id}",
                                "type": "computer",
                            },
                            {
                                "id": f"{computer_2.id}",
                                "type": "computer",
                            },
                        ],
                    },
                },
                "type": "user",
            },
            "included": [
                {
                    "attributes": {"name": computer_1.name},
                    "id": f"{computer_1.id}",
                    "type": "computer",
                },
                {
                    "attributes": {"name": computer_2.name},
                    "id": f"{computer_2.id}",
                    "type": "computer",
                },
            ],
            "jsonapi": {"version": "1.0"},
            "meta": None,
        }

    async def test_create_to_one_and_to_many_relationship_at_the_same_time(
        self,
        app: FastAPI,
        client: AsyncClient,
        computer_1: Computer,
        computer_2: Computer,
        workplace_1: Workplace,
    ):
        create_user_body = {
            "data": {
                "attributes": UserAttributesBaseSchema(
                    name=fake.name(),
                    age=fake.pyint(),
                    email=fake.email(),
                ).model_dump(),
                "relationships": {
                    "computers": {
                        "data": [
                            {
                                "id": f"{computer_1.id}",
                                "type": "computer",
                            },
                            {
                                "id": f"{computer_2.id}",
                                "type": "computer",
                            },
                        ],
                    },
                    "workplace": {
                        "data": {
                            "id": f"{workplace_1.id}",
                            "type": "workplace",
                        },
                    },
                },
            },
        }
        url = app.url_path_for("get_user_list")
        url = f"{url}?include=computers,workplace"
        res = await client.post(url, json=create_user_body)
        assert res.status_code == status.HTTP_201_CREATED, res.text

        response_data = res.json()
        assert "data" in response_data
        assert response_data["data"].pop("id")
        assert response_data == {
            "data": {
                "attributes": create_user_body["data"]["attributes"],
                "relationships": {
                    "computers": {
                        "data": [
                            {
                                "id": f"{computer_1.id}",
                                "type": "computer",
                            },
                            {
                                "id": f"{computer_2.id}",
                                "type": "computer",
                            },
                        ],
                    },
                    "workplace": {
                        "data": {
                            "id": f"{workplace_1.id}",
                            "type": "workplace",
                        },
                    },
                },
                "type": "user",
            },
            "included": [
                {
                    "attributes": {"name": computer_1.name},
                    "id": f"{computer_1.id}",
                    "type": "computer",
                },
                {
                    "attributes": {"name": computer_2.name},
                    "id": f"{computer_2.id}",
                    "type": "computer",
                },
                {
                    "attributes": {"name": workplace_1.name},
                    "id": f"{workplace_1.id}",
                    "type": "workplace",
                },
            ],
            "jsonapi": {"version": "1.0"},
            "meta": None,
        }

    async def test_create_user(self, app: FastAPI, client: AsyncClient):
        create_user_body = {
            "data": {
                "attributes": UserAttributesBaseSchema(
                    name=fake.name(),
                    age=fake.pyint(),
                    email=fake.email(),
                ).model_dump(),
            },
        }
        url = app.url_path_for("get_user_list")
        res = await client.post(url, json=create_user_body)
        assert res.status_code == status.HTTP_201_CREATED, res.text
        response_data: dict = res.json()
        assert "data" in response_data, response_data
        assert response_data["data"]["attributes"] == create_user_body["data"]["attributes"]

    async def test_create_user_and_fetch_data(self, app: FastAPI, client: AsyncClient):
        create_user_body = {
            "data": {
                "attributes": UserAttributesBaseSchema(
                    name=fake.name(),
                    age=fake.pyint(),
                    email=fake.email(),
                ).model_dump(),
            },
        }
        app.url_path_for("get_user_list")
        res = await client.post("/users/", json=create_user_body)
        assert res.status_code == status.HTTP_201_CREATED, res.text
        response_data = res.json()
        assert "data" in response_data, response_data
        assert response_data["data"]["attributes"] == create_user_body["data"]["attributes"]

        user_id = response_data["data"]["id"]

        res = await client.get(f"/users/{user_id}/")
        assert res.status_code == status.HTTP_200_OK, res.text
        response_data = res.json()
        assert "data" in response_data, response_data
        assert response_data["data"]["attributes"] == create_user_body["data"]["attributes"]
        assert response_data["data"]["id"] == user_id

    async def test_create_id_by_client(self):
        resource_type = "user_custom_b"
        app = build_app_custom(
            model=User,
            schema=UserSchema,
            schema_in_post=UserInSchemaAllowIdOnPost,
            schema_in_patch=UserPatchSchema,
            resource_type=resource_type,
        )

        new_id = f"{fake.pyint(100, 999)}"
        attrs = UserAttributesBaseSchema(
            name=fake.name(),
            age=fake.pyint(),
            email=fake.email(),
        )
        create_user_body = {
            "data": {
                "attributes": attrs.model_dump(),
                "id": new_id,
            },
        }

        async with AsyncClient(app=app, base_url="http://test") as client:
            url = app.url_path_for(f"get_{resource_type}_list")
            res = await client.post(url, json=create_user_body)
            assert res.status_code == status.HTTP_201_CREATED, res.text
            assert res.json() == {
                "data": {
                    "attributes": attrs.model_dump(),
                    "id": new_id,
                    "type": resource_type,
                },
                "jsonapi": {"version": "1.0"},
                "meta": None,
            }

    async def test_create_id_by_client_uuid_type(
        self,
        app: FastAPI,
        client: AsyncClient,
    ):
        """
        Create id (custom)

        also creates UUID field (just for testing)

        :param app:
        :param client:
        :return:
        """
        resource_type = "custom_uuid_item"

        new_id = f"{uuid4()}"
        create_attributes = CustomUUIDItemAttributesSchema(
            extra_id=uuid4(),
        )
        create_body = {
            "data": {
                "attributes": json.loads(create_attributes.json()),
                "id": new_id,
            },
        }

        url = app.url_path_for(f"get_{resource_type}_list")
        res = await client.post(url, json=create_body)
        assert res.status_code == status.HTTP_201_CREATED, res.text
        assert res.json() == {
            "data": {
                "attributes": json.loads(create_attributes.json()),
                "id": new_id,
                "type": resource_type,
            },
            "jsonapi": {"version": "1.0"},
            "meta": None,
        }

    async def test_create_with_relationship_to_the_same_table(self):
        resource_type = "self_relationship"
        app = build_app_custom(
            model=SelfRelationship,
            schema=SelfRelationshipAttributesSchema,
            resource_type=resource_type,
        )

        async with AsyncClient(app=app, base_url="http://test") as client:
            create_body = {
                "data": {
                    "attributes": {
                        "name": "parent",
                    },
                },
            }
            url = app.url_path_for(f"get_{resource_type}_list")
            res = await client.post(url, json=create_body)
            assert res.status_code == status.HTTP_201_CREATED, res.text

            response_json = res.json()
            assert response_json["data"]
            parent_object_id = response_json["data"].get("id")
            assert parent_object_id
            assert response_json == {
                "data": {
                    "attributes": {
                        "name": "parent",
                    },
                    "id": parent_object_id,
                    "type": resource_type,
                },
                "jsonapi": {"version": "1.0"},
                "meta": None,
            }

            create_with_relationship_body = {
                "data": {
                    "attributes": {
                        "name": "child",
                    },
                    "relationships": {
                        "parent_object": {
                            "data": {
                                "type": resource_type,
                                "id": parent_object_id,
                            },
                        },
                    },
                },
            }
            url = f"{url}?include=parent_object"
            res = await client.post(url, json=create_with_relationship_body)
            assert res.status_code == status.HTTP_201_CREATED, res.text

            response_json = res.json()
            assert response_json["data"]
            assert (child_object_id := response_json["data"].get("id"))
            assert res.json() == {
                "data": {
                    "attributes": {
                        "name": "child",
                    },
                    "id": child_object_id,
                    "relationships": {
                        "parent_object": {
                            "data": {
                                "id": parent_object_id,
                                "type": "self_relationship",
                            },
                        },
                    },
                    "type": "self_relationship",
                },
                "included": [
                    {
                        "attributes": {
                            "name": "parent",
                        },
                        "id": parent_object_id,
                        "type": "self_relationship",
                    },
                ],
                "jsonapi": {"version": "1.0"},
                "meta": None,
            }

    async def test_create_with_timestamp_and_fetch(self, async_session: AsyncSession):
        resource_type = "contains_timestamp_model"

        class ContainsTimestampAttrsSchema(BaseModel):
            timestamp: datetime

        app = build_app_custom(
            model=ContainsTimestamp,
            schema=ContainsTimestampAttrsSchema,
            schema_in_post=ContainsTimestampAttrsSchema,
            schema_in_patch=ContainsTimestampAttrsSchema,
            resource_type=resource_type,
        )

        create_timestamp = datetime.now(tz=timezone.utc)
        create_body = {
            "data": {
                "attributes": {
                    "timestamp": create_timestamp.isoformat(),
                },
            },
        }

        async with AsyncClient(app=app, base_url="http://test") as client:
            url = app.url_path_for(f"get_{resource_type}_list")
            res = await client.post(url, json=create_body)
            assert res.status_code == status.HTTP_201_CREATED, res.text
            response_json = res.json()

            entity_id = response_json["data"]["id"]
            assert entity_id
            assert (
                # rec
                ContainsTimestampAttrsSchema(**response_json["data"]["attributes"])
                ==
                # ex
                ContainsTimestampAttrsSchema(timestamp=create_timestamp)
            )

            # noinspection PyTypeChecker
            stms = select(ContainsTimestamp).where(ContainsTimestamp.id == int(entity_id))
            (await async_session.execute(stms)).scalar_one()

            expected_response_timestamp = create_timestamp.replace(tzinfo=None).isoformat()
            if is_postgres_tests():
                expected_response_timestamp = create_timestamp.replace().isoformat()

            params = {
                "filter": json.dumps(
                    [
                        {
                            "name": "timestamp",
                            "op": "eq",
                            "val": create_timestamp.isoformat(),
                        },
                    ],
                ).decode(),
            }

            # successfully filtered
            res = await client.get(url, params=params)
            assert res.status_code == status.HTTP_200_OK, res.text
            response_json = res.json()
            assert (
                # rec
                ContainsTimestampAttrsSchema(**response_json["data"][0]["attributes"])
                ==
                # ex
                ContainsTimestampAttrsSchema(timestamp=expected_response_timestamp)
            )

            # check filter really work
            params = {
                "filter": json.dumps(
                    [
                        {
                            "name": "timestamp",
                            "op": "eq",
                            "val": datetime.now(tz=timezone.utc).isoformat(),
                        },
                    ],
                ).decode(),
            }
            res = await client.get(url, params=params)
            assert res.status_code == status.HTTP_200_OK, res.text
            assert res.json() == {
                "meta": {"count": 0, "totalPages": 1},
                "jsonapi": {"version": "1.0"},
                "data": [],
            }

    async def test_select_custom_fields(self, app: FastAPI, client: AsyncClient):
        user_attrs_schema = UserAttributesBaseSchema(
            name=fake.name(),
            age=fake.pyint(),
            email=fake.email(),
        )
        create_user_body = {
            "data": {
                "attributes": user_attrs_schema.model_dump(),
            },
        }
        queried_user_fields = "name"
        params = QueryParams([("fields[user]", queried_user_fields)])
        url = app.url_path_for("get_user_list")
        res = await client.post(url, json=create_user_body, params=params)
        assert res.status_code == status.HTTP_201_CREATED, res.text
        response_data: dict = res.json()

        assert "data" in response_data
        assert response_data["data"].pop("id")
        assert response_data == {
            "data": {
                "attributes": user_attrs_schema.model_dump(include=set(queried_user_fields.split(","))),
                "type": "user",
            },
            "jsonapi": {"version": "1.0"},
            "meta": None,
        }


class TestPatchObjects:
    async def test_patch_object(
        self,
        app: FastAPI,
        client: AsyncClient,
        user_1: User,
    ):
        new_attrs = UserAttributesBaseSchema(
            name=fake.name(),
            age=fake.pyint(),
            email=fake.email(),
        ).model_dump()

        patch_user_body = {
            "data": {
                "id": f"{user_1.id}",
                "attributes": new_attrs,
            },
        }
        url = app.url_path_for("get_user_detail", obj_id=user_1.id)
        res = await client.patch(url, json=patch_user_body)
        assert res.status_code == status.HTTP_200_OK, res.text

        assert res.json() == {
            "data": {
                "attributes": new_attrs,
                "id": f"{user_1.id}",
                "type": "user",
            },
            "jsonapi": {"version": "1.0"},
            "meta": None,
        }

    async def test_update_schema_has_extra_fields(self, user_1: User, caplog):
        resource_type = "user_extra_fields"
        app = build_app_custom(
            model=User,
            schema=UserAttributesBaseSchema,
            schema_in_patch=CustomUserAttributesSchema,
            resource_type=resource_type,
        )

        new_attributes = CustomUserAttributesSchema(
            age=fake.pyint(),
            name=fake.user_name(),
            spam=fake.word(),
            eggs=fake.word(),
        )
        create_body = {
            "data": {
                "attributes": new_attributes.model_dump(),
                "id": f"{user_1.id}",
            },
        }

        async with AsyncClient(app=app, base_url="http://test") as client:
            url = app.url_path_for(f"update_{resource_type}_detail", obj_id=user_1.id)
            res = await client.patch(url, json=create_body)

        assert res.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert res.json()["errors"][0]["detail"] == "No fields `spam` on `User`. Make sure schema conforms model."

    async def test_select_custom_fields(
        self,
        app: FastAPI,
        client: AsyncClient,
        user_1: User,
    ):
        new_attrs = UserAttributesBaseSchema(
            name=fake.name(),
            age=fake.pyint(),
            email=fake.email(),
        )

        patch_user_body = {
            "data": {
                "id": f"{user_1.id}",
                "attributes": new_attrs.model_dump(),
            },
        }
        queried_user_fields = "name"
        params = QueryParams([("fields[user]", queried_user_fields)])
        url = app.url_path_for("get_user_detail", obj_id=user_1.id)
        res = await client.patch(url, params=params, json=patch_user_body)

        assert res.status_code == status.HTTP_200_OK, res.text
        assert res.json() == {
            "data": {
                "attributes": new_attrs.model_dump(include=set(queried_user_fields.split(","))),
                "id": f"{user_1.id}",
                "type": "user",
            },
            "jsonapi": {"version": "1.0"},
            "meta": None,
        }

    @pytest.mark.parametrize("check_type", ["ok", "fail"])
    async def test_update_to_many_relationships(
        self,
        async_session: AsyncSession,
        check_type: Literal["ok", "fail"],
        # clear_schemas_storage,
    ):
        resource_type = "cascade_case"

        app = build_app_custom(
            model=CascadeCase,
            schema=CascadeCaseSchema,
            resource_type=resource_type,
        )

        top_item = CascadeCase()
        new_top_item = CascadeCase()
        sub_item_1 = CascadeCase(parent_item=top_item)
        sub_item_2 = CascadeCase(parent_item=top_item)
        async_session.add_all(
            [
                top_item,
                new_top_item,
                sub_item_1,
                sub_item_2,
            ],
        )
        await async_session.commit()

        assert sub_item_1.parent_item_id == top_item.id
        assert sub_item_2.parent_item_id == top_item.id

        async with AsyncClient(app=app, base_url="http://test") as client:
            params = None
            if check_type == "ok":
                params = {"include": "sub_items"}

            update_body = {
                "type": resource_type,
                "data": {
                    "id": f"{new_top_item.id}",
                    "attributes": {},
                    "relationships": {
                        "sub_items": {
                            "data": [
                                {
                                    "type": resource_type,
                                    "id": f"{sub_item_1.id}",
                                },
                                {
                                    "type": resource_type,
                                    "id": f"{sub_item_2.id}",
                                },
                            ],
                        },
                    },
                },
            }
            url = app.url_path_for(f"update_{resource_type}_detail", obj_id=new_top_item.id)

            res = await client.patch(url, params=params, json=update_body)

            if check_type == "ok":
                assert res.status_code == status.HTTP_200_OK, res.text

                await async_session.refresh(sub_item_1)
                await async_session.refresh(sub_item_2)
                await async_session.refresh(top_item)
                assert sub_item_1.parent_item_id == new_top_item.id
                assert sub_item_1.parent_item_id == new_top_item.id
            else:
                assert res.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR, res.text
                assert res.json() == {
                    "errors": [
                        {
                            "detail": "Error of loading the 'sub_items' relationship. "
                            "Please add this relationship to include query parameter explicitly.",
                            "source": {"parameter": "include"},
                            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                            "title": "Internal Server Error",
                        },
                    ],
                }


class TestPatchObjectRelationshipsToOne:
    async def test_ok_when_foreign_key_of_related_object_is_nullable(
        self,
        app: FastAPI,
        client: AsyncClient,
        user_1: User,
        workplace_1: Workplace,
        workplace_2: Workplace,
    ):
        new_attrs = UserAttributesBaseSchema(
            name=fake.name(),
            age=fake.pyint(),
            email=fake.email(),
        ).model_dump()

        patch_user_body = {
            "data": {
                "id": f"{user_1.id}",
                "attributes": new_attrs,
                "relationships": {
                    "workplace": {
                        "data": {
                            "type": "workplace",
                            "id": f"{workplace_1.id}",
                        },
                    },
                },
            },
        }

        url = app.url_path_for("get_user_detail", obj_id=user_1.id)
        url = f"{url}?include=workplace"
        # create relationship with patch endpoint
        res = await client.patch(url, json=patch_user_body)
        assert res.status_code == status.HTTP_200_OK, res.text

        assert res.json() == {
            "data": {
                "attributes": new_attrs,
                "id": f"{user_1.id}",
                "relationships": {
                    "workplace": {
                        "data": {
                            "type": "workplace",
                            "id": f"{workplace_1.id}",
                        },
                    },
                },
                "type": "user",
            },
            "included": [
                {
                    "attributes": {
                        "name": workplace_1.name,
                    },
                    "id": f"{workplace_1.id}",
                    "type": "workplace",
                },
            ],
            "jsonapi": {"version": "1.0"},
            "meta": None,
        }

        patch_user_body["data"]["relationships"]["workplace"]["data"]["id"] = f"{workplace_2.id}"

        # update relationship with patch endpoint
        res = await client.patch(url, json=patch_user_body)
        assert res.status_code == status.HTTP_200_OK, res.text

        assert res.json() == {
            "data": {
                "attributes": new_attrs,
                "id": f"{user_1.id}",
                "relationships": {
                    "workplace": {
                        "data": {
                            "type": "workplace",
                            "id": f"{workplace_2.id}",
                        },
                    },
                },
                "type": "user",
            },
            "included": [
                {
                    "attributes": {
                        "name": workplace_2.name,
                    },
                    "id": f"{workplace_2.id}",
                    "type": "workplace",
                },
            ],
            "jsonapi": {"version": "1.0"},
            "meta": None,
        }

    async def test_fail_to_bind_relationship_with_constraint(
        self,
        app: FastAPI,
        client: AsyncClient,
        user_1: User,
        user_2: User,
        user_1_bio: UserBio,
        user_2_bio: UserBio,
    ):
        assert user_1_bio.user_id == user_1.id, "use user bio 1 for user 1"
        assert user_2_bio.user_id == user_2.id, "we need user_2 to be bound to user_bio_2"

        patch_user_bio_body = {
            "data": {
                "id": f"{user_1_bio.id}",
                "attributes": UserBioAttributesBaseSchema.model_validate(user_1_bio).model_dump(),
                "relationships": {
                    "user": {
                        "data": {
                            "type": "user",
                            "id": f"{user_2.id}",
                        },
                    },
                },
            },
        }

        url = app.url_path_for("get_user_bio_detail", obj_id=user_1_bio.id)
        url = f"{url}?include=user"
        res = await client.patch(url, json=patch_user_bio_body)
        assert res.status_code == status.HTTP_400_BAD_REQUEST, res.text
        assert res.json() == {
            "errors": [
                {
                    "detail": "Could not update object",
                    "source": {"pointer": "/data"},
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "title": "Bad Request",
                    "meta": {
                        "id": f"{user_1_bio.id}",
                        "type": "user_bio",
                    },
                },
            ],
        }

    async def test_relationship_not_found(
        self,
        app: FastAPI,
        client: AsyncClient,
        user_1: User,
    ):
        new_attrs = UserAttributesBaseSchema(
            name=fake.name(),
            age=fake.pyint(),
            email=fake.email(),
        ).model_dump()

        fake_relationship_id = "1"
        patch_user_body = {
            "data": {
                "id": f"{user_1.id}",
                "attributes": new_attrs,
                "relationships": {
                    "workplace": {
                        "data": {
                            "type": "workplace",
                            "id": fake_relationship_id,
                        },
                    },
                },
            },
        }

        url = app.url_path_for("get_user_detail", obj_id=user_1.id)
        url = f"{url}?include=workplace"
        # create relationship with patch endpoint
        res = await client.patch(url, json=patch_user_body)
        assert res.status_code == status.HTTP_404_NOT_FOUND, res.text

        assert res.json() == {
            "errors": [
                {
                    "detail": f"Objects for Workplace with ids: ['{fake_relationship_id}'] not found",
                    "source": {"pointer": "/data"},
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "title": "Related object not found.",
                },
            ],
        }

    async def test_update_resource_error_same_id(
        self,
        app: FastAPI,
        client: AsyncClient,
        user_1: User,
    ):
        patch_user_body = {
            "data": {
                "id": f"{user_1.id}",
                "attributes": UserAttributesBaseSchema.model_validate(user_1).model_dump(),
            },
        }

        url = app.url_path_for("get_user_detail", obj_id=0)
        res = await client.patch(url, json=patch_user_body)
        assert res.status_code == status.HTTP_400_BAD_REQUEST, res.text
        assert res.json() == {
            "errors": [
                {
                    "detail": "obj_id and data.id should be same.",
                    "source": {"pointer": "/data/id"},
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "title": "Bad Request",
                },
            ],
        }

    async def test_remove_to_one_relationship_using_by_update(self, async_session: AsyncSession):
        resource_type = "self_relationship"

        app = build_app_custom(
            model=SelfRelationship,
            schema=SelfRelationshipAttributesSchema,
            resource_type=resource_type,
        )

        parent_obj = SelfRelationship(name=fake.name())
        child_obj = SelfRelationship(name=fake.name(), parent_object=parent_obj)
        async_session.add_all([parent_obj, child_obj])
        await async_session.commit()

        assert child_obj.self_relationship_id == parent_obj.id

        async with AsyncClient(app=app, base_url="http://test") as client:
            expected_name = fake.name()
            update_body = {
                "data": {
                    "id": f"{child_obj.id}",
                    "attributes": {
                        "name": expected_name,
                    },
                    "relationships": {
                        "parent_object": {
                            "data": None,
                        },
                    },
                },
            }
            params = {
                "include": "parent_object",
            }
            url = app.url_path_for(f"update_{resource_type}_detail", obj_id=child_obj.id)
            res = await client.patch(url, params=params, json=update_body)
            assert res.status_code == status.HTTP_200_OK, res.text
            assert res.json() == {
                "data": {
                    "attributes": SelfRelationshipAttributesSchema(name=expected_name).model_dump(exclude_unset=True),
                    "id": f"{child_obj.id}",
                    "relationships": {
                        "parent_object": {
                            "data": None,
                        },
                    },
                    "type": "self_relationship",
                },
                "included": [],
                "jsonapi": {"version": "1.0"},
                "meta": None,
            }

            await async_session.refresh(child_obj)
            assert child_obj.self_relationship_id is None


class TestPatchRelationshipsToMany:
    async def test_ok(
        self,
        app: FastAPI,
        client: AsyncClient,
        user_1: User,
        computer_1: Computer,
        computer_2: Computer,
    ):
        new_attrs = UserAttributesBaseSchema(
            name=fake.name(),
            age=fake.pyint(),
            email=fake.email(),
        ).model_dump()

        patch_user_body = {
            "data": {
                "id": f"{user_1.id}",
                "attributes": new_attrs,
                "relationships": {
                    "computers": {
                        "data": [
                            {
                                "type": "computer",
                                # test id as int
                                "id": f"{computer_1.id}",
                            },
                            {
                                "type": "computer",
                                # test id as str
                                "id": f"{computer_2.id}",
                            },
                        ],
                    },
                },
            },
        }

        url = app.url_path_for("get_user_detail", obj_id=user_1.id)
        url = f"{url}?include=computers"
        res = await client.patch(url, json=patch_user_body)
        assert res.status_code == status.HTTP_200_OK, res.text

        assert res.json() == {
            "data": {
                "attributes": new_attrs,
                "id": f"{user_1.id}",
                "relationships": {
                    "computers": {
                        "data": [
                            {
                                "type": "computer",
                                "id": f"{computer_1.id}",
                            },
                            {
                                "type": "computer",
                                "id": f"{computer_2.id}",
                            },
                        ],
                    },
                },
                "type": "user",
            },
            "included": [
                {
                    "attributes": {
                        "name": computer_1.name,
                    },
                    "id": f"{computer_1.id}",
                    "type": "computer",
                },
                {
                    "attributes": {
                        "name": computer_2.name,
                    },
                    "id": f"{computer_2.id}",
                    "type": "computer",
                },
            ],
            "jsonapi": {"version": "1.0"},
            "meta": None,
        }

        patch_user_body["data"]["relationships"]["computers"] = {
            "data": [
                {
                    "type": "computer",
                    "id": f"{computer_1.id}",
                },
            ],
        }

        # update relationships with patch endpoint
        res = await client.patch(url, json=patch_user_body)
        assert res.status_code == status.HTTP_200_OK, res.text

        assert res.json() == {
            "data": {
                "attributes": new_attrs,
                "id": f"{user_1.id}",
                "relationships": {
                    "computers": {
                        "data": [
                            {
                                "type": "computer",
                                "id": f"{computer_1.id}",
                            },
                        ],
                    },
                },
                "type": "user",
            },
            "included": [
                {
                    "attributes": {
                        "name": computer_1.name,
                    },
                    "id": f"{computer_1.id}",
                    "type": "computer",
                },
            ],
            "jsonapi": {"version": "1.0"},
            "meta": None,
        }

    async def test_relationship_not_found(
        self,
        app: FastAPI,
        client: AsyncClient,
        user_1: User,
        computer_1: Computer,
        computer_2: Computer,
    ):
        new_attrs = UserAttributesBaseSchema(
            name=fake.name(),
            age=fake.pyint(),
            email=fake.email(),
        ).model_dump()

        fake_computer_id = fake.pyint(min_value=1000, max_value=9999)
        assert fake_computer_id != computer_2.id

        patch_user_body = {
            "data": {
                "id": f"{user_1.id}",
                "attributes": new_attrs,
                "relationships": {
                    "computers": {
                        "data": [
                            {
                                "type": "computer",
                                "id": f"{computer_1.id}",
                            },
                            {
                                "type": "computer",
                                "id": f"{fake_computer_id}",
                            },
                        ],
                    },
                },
            },
        }

        url = app.url_path_for("get_user_detail", obj_id=user_1.id)
        url = f"{url}?include=computers"
        # update relationships with patch endpoint
        res = await client.patch(url, json=patch_user_body)
        assert res.status_code == status.HTTP_404_NOT_FOUND, res.text

        assert res.json() == {
            "errors": [
                {
                    "detail": f"Objects for Computer with ids: ['{fake_computer_id}'] not found",
                    "source": {"pointer": "/data"},
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "title": "Related object not found.",
                },
            ],
        }

    async def test_remove_to_many_relationship_using_by_update(self, async_session: AsyncSession):
        resource_type = "self_relationship"

        app = build_app_custom(
            model=SelfRelationship,
            schema=SelfRelationshipAttributesSchema,
            resource_type=resource_type,
        )

        parent_obj = SelfRelationship(name=fake.name())
        child_obj_1 = SelfRelationship(name=fake.name(), parent_object=parent_obj)
        child_obj_2 = SelfRelationship(name=fake.name(), parent_object=parent_obj)
        async_session.add_all([parent_obj, child_obj_1, child_obj_2])
        await async_session.commit()

        assert child_obj_1.self_relationship_id == parent_obj.id
        assert child_obj_2.self_relationship_id == parent_obj.id
        assert len(parent_obj.children_objects) == 2  # noqa PLR2004

        async with AsyncClient(app=app, base_url="http://test") as client:
            expected_name = fake.name()
            update_body = {
                "data": {
                    "id": f"{parent_obj.id}",
                    "attributes": {
                        "name": expected_name,
                    },
                    "relationships": {
                        "children_objects": {
                            "data": [],
                        },
                    },
                },
            }
            params = {
                "include": "children_objects",
            }
            url = app.url_path_for(f"update_{resource_type}_detail", obj_id=parent_obj.id)
            res = await client.patch(url, params=params, json=update_body)
            assert res.status_code == status.HTTP_200_OK, res.text
            assert res.json() == {
                "data": {
                    "attributes": SelfRelationshipAttributesSchema(name=expected_name).model_dump(exclude_unset=True),
                    "id": f"{parent_obj.id}",
                    "relationships": {"children_objects": {"data": []}},
                    "type": "self_relationship",
                },
                "included": [],
                "jsonapi": {"version": "1.0"},
                "meta": None,
            }

            await async_session.refresh(child_obj_1)
            await async_session.refresh(child_obj_2)
            assert child_obj_1.self_relationship_id is None
            assert child_obj_2.self_relationship_id is None


class TestDeleteObjects:
    async def test_delete_object_and_fetch_404(
        self,
        app: FastAPI,
        client: AsyncClient,
        user_1: User,
    ):
        url = app.url_path_for("get_user_detail", obj_id=user_1.id)
        res = await client.delete(url)
        assert res.status_code == status.HTTP_204_NO_CONTENT, res.text
        assert res.content == b""

        res = await client.get(url)
        assert res.status_code == status.HTTP_404_NOT_FOUND, res.text

        url = app.url_path_for("get_user_list")
        res = await client.get(url)
        assert res.status_code == status.HTTP_200_OK, res.text
        assert res.json() == {
            "data": [],
            "jsonapi": {"version": "1.0"},
            "meta": {"count": 0, "totalPages": 1},
        }

    async def test_delete_objects_many(
        self,
        app: FastAPI,
        client: AsyncClient,
        user_1: User,
        user_2: User,
        user_3: User,
    ):
        params = {
            "filter": json.dumps(
                [
                    {
                        "name": "id",
                        "op": "in",
                        "val": [
                            user_1.id,
                            user_3.id,
                        ],
                    },
                ],
            ).decode(),
        }

        url = app.url_path_for("get_user_list")
        res = await client.delete(url, params=params)
        assert res.status_code == status.HTTP_200_OK, res.text
        assert res.json() == {
            "data": [
                {
                    "attributes": UserAttributesBaseSchema.model_validate(user_1).model_dump(),
                    "id": f"{user_1.id}",
                    "type": "user",
                },
                {
                    "attributes": UserAttributesBaseSchema.model_validate(user_3).model_dump(),
                    "id": f"{user_3.id}",
                    "type": "user",
                },
            ],
            "jsonapi": {"version": "1.0"},
            "meta": {"count": 2, "totalPages": 1},
        }

        res = await client.get(url)
        assert res.status_code == status.HTTP_200_OK, res.text
        assert res.json() == {
            "data": [
                {
                    "attributes": UserAttributesBaseSchema.model_validate(user_2).model_dump(),
                    "id": f"{user_2.id}",
                    "type": "user",
                },
            ],
            "jsonapi": {"version": "1.0"},
            "meta": {"count": 1, "totalPages": 1},
        }

    async def test_select_custom_fields(
        self,
        app: FastAPI,
        client: AsyncClient,
        user_1: User,
        user_2: User,
    ):
        queried_user_fields = "name"
        params = QueryParams(
            [
                ("fields[user]", queried_user_fields),
                ("sort", "id"),
            ],
        )
        url = app.url_path_for("get_user_list")
        res = await client.delete(url, params=params)
        assert res.status_code == status.HTTP_200_OK, res.text
        assert res.json() == {
            "data": [
                {
                    "attributes": UserAttributesBaseSchema.model_validate(user_1).model_dump(
                        include=set(queried_user_fields.split(",")),
                    ),
                    "id": f"{user_1.id}",
                    "type": "user",
                },
                {
                    "attributes": UserAttributesBaseSchema.model_validate(user_2).model_dump(
                        include=set(queried_user_fields.split(",")),
                    ),
                    "id": f"{user_2.id}",
                    "type": "user",
                },
            ],
            "jsonapi": {"version": "1.0"},
            "meta": {"count": 2, "totalPages": 1},
        }

    async def test_cascade_delete(self, async_session: AsyncSession):
        resource_type = "cascade_case"

        app = build_app_custom(
            model=CascadeCase,
            schema=CascadeCaseSchema,
            resource_type=resource_type,
        )

        top_item = CascadeCase()
        sub_item_1 = CascadeCase(parent_item=top_item)
        sub_item_2 = CascadeCase(parent_item=top_item)
        async_session.add_all(
            [
                top_item,
                sub_item_1,
                sub_item_2,
            ],
        )
        await async_session.commit()

        assert sub_item_1.parent_item_id == top_item.id
        assert sub_item_2.parent_item_id == top_item.id

        async with AsyncClient(app=app, base_url="http://test") as client:
            url = app.url_path_for(f"delete_{resource_type}_detail", obj_id=top_item.id)

            res = await client.delete(url)
            assert res.status_code == status.HTTP_204_NO_CONTENT, res.text

            top_item_stmt = select(CascadeCase).where(CascadeCase.id == top_item.id)
            top_item = (await async_session.execute(top_item_stmt)).one_or_none()
            assert top_item is None

            sub_items_stmt = select(CascadeCase).where(CascadeCase.id.in_([sub_item_1.id, sub_item_2.id]))
            sub_items = (await async_session.execute(sub_items_stmt)).all()
            assert sub_items == []


class TestOpenApi:
    def test_openapi_method_ok(self, app: FastAPI):
        data = app.openapi()
        assert isinstance(data, dict)

    async def test_openapi_endpoint_ok(self, client: AsyncClient, app: FastAPI):
        response = await client.get(app.openapi_url)
        assert response.status_code == status.HTTP_200_OK, response.text
        resp = response.json()
        assert isinstance(resp, dict)

    async def test_openapi_for_client_can_set_id(self):
        class Schema(BaseModel):
            id: Annotated[UUID, ClientCanSetId()]

        app = build_app_custom(
            model=User,
            schema=Schema,
            schema_in_post=Schema,
            schema_in_patch=Schema,
            resource_type="openapi_case_1",
        )

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(app.openapi_url)
            assert response.status_code == status.HTTP_200_OK, response.text


class TestFilters:
    async def test_filters_really_works(
        self,
        client: AsyncClient,
        user_1: User,
        user_2: User,
    ):
        fake_name = fake.name()
        params = {"filter[name]": fake_name}
        assert user_1.name != fake_name
        assert user_2.name != fake_name
        res = await client.get("/users/", params=params)
        assert res.status_code == status.HTTP_200_OK, res.text
        assert res.json() == {
            "data": [],
            "jsonapi": {"version": "1.0"},
            "meta": {"count": 0, "totalPages": 1},
        }

    @pytest.mark.parametrize(
        "field_name",
        [pytest.param(name, id=name) for name in ["id", "name", "age", "email"]],
    )
    async def test_field_filters(
        self,
        app: FastAPI,
        client: AsyncClient,
        user_1: User,
        user_2: User,
        field_name: str,
    ):
        filter_value = getattr(user_1, field_name)
        assert getattr(user_2, field_name) != filter_value

        params = {f"filter[{field_name}]": filter_value}
        url = app.url_path_for("get_user_list")
        res = await client.get(url, params=params)
        assert res.status_code == status.HTTP_200_OK, res.text
        assert res.json() == {
            "data": [
                {
                    "attributes": UserAttributesBaseSchema.model_validate(user_1).model_dump(),
                    "id": f"{user_1.id}",
                    "type": "user",
                },
            ],
            "jsonapi": {"version": "1.0"},
            "meta": {"count": 1, "totalPages": 1},
        }

    async def test_several_field_filters_at_the_same_time(
        self,
        app: FastAPI,
        client: AsyncClient,
        user_1: User,
        user_2: User,
    ):
        params = {
            f"filter[{field_name}]": getattr(user_1, field_name)
            for field_name in [
                "id",
                "name",
                "age",
                "email",
            ]
        }
        assert user_2.id != user_1.id
        url = app.url_path_for("get_user_list")
        res = await client.get(url, params=params)
        assert res.status_code == status.HTTP_200_OK, res.text
        assert res.json() == {
            "data": [
                {
                    "attributes": UserAttributesBaseSchema.model_validate(user_1).model_dump(),
                    "id": f"{user_1.id}",
                    "type": "user",
                },
            ],
            "jsonapi": {"version": "1.0"},
            "meta": {"count": 1, "totalPages": 1},
        }

    async def test_field_filters_with_values_from_different_models(
        self,
        app: FastAPI,
        client: AsyncClient,
        user_1: User,
        user_2: User,
    ):
        params_user_1 = {"filter[name]": user_1.name}

        assert user_1.age != user_2.age
        params_user_2 = {"filter[age]": user_2.age}

        url = app.url_path_for("get_user_list")
        res = await client.get(url, params=params_user_2 | params_user_1)
        assert res.status_code == status.HTTP_200_OK, res.text
        assert res.json() == {
            "data": [],
            "jsonapi": {"version": "1.0"},
            "meta": {"count": 0, "totalPages": 1},
        }

    @pytest.mark.parametrize(
        ("filter_dict", "expected_email_is_null"),
        [
            pytest.param([{"name": "email", "op": "is_", "val": None}], True),
            pytest.param([{"name": "email", "op": "isnot", "val": None}], False),
        ],
    )
    async def test_filter_by_null(
        self,
        app: FastAPI,
        async_session: AsyncSession,
        client: AsyncClient,
        user_1: User,
        user_2: User,
        filter_dict: dict,
        expected_email_is_null: bool,
    ):
        user_2.email = None
        await async_session.commit()

        target_user = user_2 if expected_email_is_null else user_1

        url = app.url_path_for("get_user_list")
        params = {"filter": json.dumps(filter_dict).decode()}

        response = await client.get(url, params=params)
        assert response.status_code == status.HTTP_200_OK, response.text

        response_json = response.json()

        assert len(data := response_json["data"]) == 1
        assert data[0]["id"] == f"{target_user.id}"
        assert data[0]["attributes"]["email"] == target_user.email

    async def test_filter_by_null_error_when_null_is_not_possible_value(
        self,
        async_session: AsyncSession,
        user_1: User,
    ):
        resource_type = "user_with_nullable_email"

        class UserWithNotNullableEmailSchema(UserSchema):
            email: str

        app = build_app_custom(
            model=User,
            schema=UserWithNotNullableEmailSchema,
            schema_in_post=UserWithNotNullableEmailSchema,
            schema_in_patch=UserWithNotNullableEmailSchema,
            resource_type=resource_type,
        )
        user_1.email = None
        await async_session.commit()

        url = app.url_path_for(f"get_{resource_type}_list")
        params = {
            "filter": json.dumps(
                [
                    {
                        "name": "email",
                        "op": "is_",
                        "val": None,
                    },
                ],
            ).decode(),
        }

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(url, params=params)
            assert response.status_code == status.HTTP_400_BAD_REQUEST, response.text
            assert response.json() == {
                "errors": [
                    {
                        "detail": "The field `email` can't be null.",
                        "source": {"parameter": "filters"},
                        "status_code": status.HTTP_400_BAD_REQUEST,
                        "title": "Invalid filters querystring parameter.",
                    },
                ],
            }

    async def test_custom_sql_filter_lower_string(
        self,
        async_session: AsyncSession,
        user_1: User,
        user_2: User,
    ):
        resource_type = "user_with_custom_lower_filter"

        assert user_1.id != user_2.id

        class UserWithEmailFieldSchema(UserAttributesBaseSchema):
            email: Annotated[str, sql_filter_lower_equals]

        app = build_app_custom(
            model=User,
            schema=UserWithEmailFieldSchema,
            resource_type=resource_type,
        )

        name, _, domain = user_1.email.partition("@")
        user_1.email = f"{name.upper()}@{domain}"
        await async_session.commit()
        params = {
            "filter": json.dumps(
                [
                    {
                        "name": "email",
                        "op": "lower_equals",
                        "val": f"{name}@{domain.upper()}",
                    },
                ],
            ).decode(),
        }
        url = app.url_path_for(f"get_{resource_type}_list")
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(url, params=params)
            assert response.status_code == status.HTTP_200_OK, response.text
            response_data = response.json()["data"]

        assert len(response_data) == 1
        assert response_data[0] == {
            "id": f"{user_1.id}",
            "type": resource_type,
            "attributes": UserWithEmailFieldSchema.model_validate(user_1).model_dump(),
        }

    async def test_custom_sql_filter_lower_string_old_style_with_joins(
        self,
        caplog,
        async_session: AsyncSession,
        user_1: User,
        user_2: User,
    ):
        resource_type = "user_with_custom_lower_filter_old_style_joins"

        assert user_1.id != user_2.id

        class UserWithEmailFieldFilterSchema(UserAttributesBaseSchema):
            email: Annotated[str, sql_filter_lower_equals]

        app = build_app_custom(
            model=User,
            schema=UserWithEmailFieldFilterSchema,
            resource_type=resource_type,
        )

        name, _, domain = user_1.email.partition("@")
        user_1.email = f"{name.upper()}@{domain}"
        await async_session.commit()
        params = {
            "filter": json.dumps(
                [
                    {
                        "name": "email",
                        "op": "lower_equals",
                        "val": f"{name}@{domain.upper()}",
                    },
                ],
            ).decode(),
        }
        url = app.url_path_for(f"get_{resource_type}_list")
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(url, params=params)
            assert response.status_code == status.HTTP_200_OK, response.text
            response_data = response.json()["data"]

        assert len(response_data) == 1
        assert response_data[0] == {
            "id": f"{user_1.id}",
            "type": resource_type,
            "attributes": UserWithEmailFieldFilterSchema.model_validate(user_1).model_dump(),
        }

    async def test_custom_sql_filter_invalid_result(
        self,
        caplog,
        async_session: AsyncSession,
        user_1: User,
    ):
        resource_type = "user_with_custom_invalid_sql_filter"

        class UserWithInvalidEmailFieldFilterSchema(UserAttributesBaseSchema):
            email: str

        app = build_app_custom(
            model=User,
            schema=UserWithInvalidEmailFieldFilterSchema,
            resource_type=resource_type,
        )

        field_name = "email"
        field_op = "custom_broken_filter"
        params = {
            "filter": json.dumps(
                [
                    {
                        "name": field_name,
                        "op": field_op,
                        "val": "qwerty",
                    },
                ],
            ).decode(),
        }
        url = app.url_path_for(f"get_{resource_type}_list")
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(url, params=params)
            assert response.status_code == status.HTTP_400_BAD_REQUEST, response.text
            assert response.json() == {
                "errors": [
                    {
                        "detail": f"Field {field_name!r} has no operator {field_op!r}",
                        "source": {"parameter": "filters"},
                        "status_code": status.HTTP_400_BAD_REQUEST,
                        "title": "Invalid filters querystring parameter.",
                    },
                ],
            }

    async def test_composite_filter_by_one_field(
        self,
        app: FastAPI,
        client: AsyncClient,
        user_1: User,
        user_2: User,
        user_3: User,
    ):
        params = {
            "filter": json.dumps(
                [
                    {
                        "name": "id",
                        "op": "in",
                        "val": [
                            user_1.id,
                            user_3.id,
                        ],
                    },
                ],
            ).decode(),
        }

        url = app.url_path_for("get_user_list")
        res = await client.get(url, params=params)
        assert res.status_code == status.HTTP_200_OK, res.text
        assert res.json() == {
            "data": [
                {
                    "attributes": UserAttributesBaseSchema.model_validate(user_1).model_dump(),
                    "id": f"{user_1.id}",
                    "type": "user",
                },
                {
                    "attributes": UserAttributesBaseSchema.model_validate(user_3).model_dump(),
                    "id": f"{user_3.id}",
                    "type": "user",
                },
            ],
            "jsonapi": {"version": "1.0"},
            "meta": {"count": 2, "totalPages": 1},
        }

    async def test_composite_filter_by_several_fields(
        self,
        app: FastAPI,
        client: AsyncClient,
        user_1: User,
        user_2: User,
        user_3: User,
    ):
        params = {
            "filter": json.dumps(
                [
                    {
                        "name": "id",
                        "op": "in",
                        "val": [
                            user_1.id,
                            user_3.id,
                        ],
                    },
                    {
                        "name": "name",
                        "op": "eq",
                        "val": user_1.name,
                    },
                ],
            ).decode(),
        }

        url = app.url_path_for("get_user_list")
        res = await client.get(url, params=params)
        assert res.status_code == status.HTTP_200_OK, res.text
        assert res.json() == {
            "data": [
                {
                    "attributes": UserAttributesBaseSchema.model_validate(user_1).model_dump(),
                    "id": f"{user_1.id}",
                    "type": "user",
                },
            ],
            "jsonapi": {"version": "1.0"},
            "meta": {"count": 1, "totalPages": 1},
        }

    async def test_composite_filter_with_mutually_exclusive_conditions(
        self,
        app: FastAPI,
        client: AsyncClient,
        user_1: User,
        user_2: User,
        user_3: User,
    ):
        params = {
            "filter": json.dumps(
                [
                    {
                        "name": "id",
                        "op": "in",
                        "val": [
                            user_1.id,
                            user_3.id,
                        ],
                    },
                    {
                        "name": "id",
                        "op": "eq",
                        "val": user_2.id,
                    },
                ],
            ).decode(),
        }

        url = app.url_path_for("get_user_list")
        res = await client.get(url, params=params)
        assert res.status_code == status.HTTP_200_OK, res.text
        assert res.json() == {
            "data": [],
            "jsonapi": {"version": "1.0"},
            "meta": {"count": 0, "totalPages": 1},
        }

    async def test_filter_with_nested_conditions(
        self,
        app: FastAPI,
        async_session: AsyncSession,
        client: AsyncClient,
    ):
        workplace_name = "Common workplace name"

        workplace_1, workplace_2, workplace_3, workplace_4 = (
            await create_workplace(async_session, name=workplace_name),
            await create_workplace(async_session, name=workplace_name),
            await create_workplace(async_session, name=workplace_name),
            await create_workplace(async_session, name=workplace_name),
        )

        user_1, user_2, _, user_4 = (
            await create_user(async_session, name="John Doe", age=20, workplace=workplace_1),
            await create_user(async_session, name="Jane Doe", age=25, workplace=workplace_2),
            await create_user(async_session, name="Jonny Doe", age=30, workplace=workplace_3),
            await create_user(async_session, name="Mary Jane", age=21, workplace=workplace_4),
        )

        params = {
            "filter": json.dumps(
                [
                    {
                        "name": "workplace.name",
                        "op": "eq",
                        "val": workplace_name,
                    },
                    {
                        "or": [
                            {
                                "not": {
                                    "name": "name",
                                    "op": "ne",
                                    "val": "Mary Jane",
                                },
                            },
                            {
                                "and": [
                                    {
                                        "name": "name",
                                        "op": "like",
                                        "val": "%Doe%",
                                    },
                                    {
                                        "name": "age",
                                        "op": "lt",
                                        "val": 30,
                                    },
                                ],
                            },
                        ],
                    },
                ],
            ).decode(),
        }

        url = app.url_path_for("get_user_list")
        res = await client.get(url, params=params)
        assert res.status_code == status.HTTP_200_OK, res.text
        assert res.json() == {
            "data": [
                {
                    "attributes": UserAttributesBaseSchema.model_validate(user_1).model_dump(),
                    "id": f"{user_1.id}",
                    "type": "user",
                },
                {
                    "attributes": UserAttributesBaseSchema.model_validate(user_2).model_dump(),
                    "id": f"{user_2.id}",
                    "type": "user",
                },
                {
                    "attributes": UserAttributesBaseSchema.model_validate(user_4).model_dump(),
                    "id": f"{user_4.id}",
                    "type": "user",
                },
            ],
            "jsonapi": {"version": "1.0"},
            "meta": {"count": 3, "totalPages": 1},
        }

    async def test_join_by_relationships_does_not_duplicating_response_entities(
        self,
        app: FastAPI,
        async_session: AsyncSession,
        client: AsyncClient,
        user_1: User,
        user_1_post: PostComment,
    ):
        text = fake.sentence()
        comment_1 = PostComment(
            text=text,
            post_id=user_1_post.id,
            user_id=user_1.id,
        )
        comment_2 = PostComment(
            text=text,
            post_id=user_1_post.id,
            user_id=user_1.id,
        )
        async_session.add_all([comment_1, comment_2])
        await async_session.commit()

        params = {
            "filter": json.dumps(
                [
                    {
                        "name": "posts.comments.text",
                        "op": "eq",
                        "val": text,
                    },
                ],
            ).decode(),
        }

        url = app.url_path_for("get_user_list")
        res = await client.get(url, params=params)
        assert res.status_code == status.HTTP_200_OK, res.text
        assert res.json() == {
            "data": [
                {
                    "attributes": UserAttributesBaseSchema.model_validate(user_1).model_dump(),
                    "id": f"{user_1.id}",
                    "type": "user",
                },
            ],
            "jsonapi": {"version": "1.0"},
            "meta": {"count": 1, "totalPages": 1},
        }

    async def test_sqla_filters_by_uuid_type(
        self,
        async_session: AsyncSession,
    ):
        """
        This test checks if UUID fields allow filtering by UUID object

        Make sure your UUID field allows native UUID filtering: `UUID(as_uuid=True)`

        :param async_session:
        :return:
        """
        new_id = uuid4()
        extra_id = uuid4()
        item = CustomUUIDItem(
            id=new_id,
            extra_id=extra_id,
        )
        async_session.add(item)
        await async_session.commit()

        # noinspection PyTypeChecker
        stmt = select(CustomUUIDItem)
        # works because we set `as_uuid=True`
        i = await async_session.scalar(stmt.where(CustomUUIDItem.id == new_id))
        assert i
        # works because we set `as_uuid=True`
        i = await async_session.scalar(stmt.where(CustomUUIDItem.extra_id == extra_id))
        assert i

    @pytest.mark.parametrize("filter_kind", ["small", "full"])
    async def test_filter_by_field_of_uuid_type(
        self,
        app: FastAPI,
        client: AsyncClient,
        async_session: AsyncSession,
        filter_kind: Literal["small", "full"],
    ):
        resource_type = "custom_uuid_item"

        new_id = uuid4()
        extra_id = uuid4()
        item = CustomUUIDItem(
            id=new_id,
            extra_id=extra_id,
        )
        another_item = CustomUUIDItem(
            id=uuid4(),
            extra_id=uuid4(),
        )
        async_session.add(item)
        async_session.add(another_item)
        await async_session.commit()

        params = {}
        if filter_kind == "small":
            params.update(
                {
                    "filter[extra_id]": f"{extra_id}",
                },
            )
        else:
            params.update(
                {
                    "filter": json.dumps(
                        [
                            {
                                "name": "extra_id",
                                "op": "eq",
                                "val": f"{extra_id}",
                            },
                        ],
                    ).decode(),
                },
            )

        url = app.url_path_for(f"get_{resource_type}_list")
        res = await client.get(url, params=params)
        assert res.status_code == status.HTTP_200_OK, res.text
        assert res.json() == {
            "data": [
                {
                    "attributes": json.loads(CustomUUIDItemAttributesSchema.model_validate(item).model_dump_json()),
                    "id": f"{new_id}",
                    "type": resource_type,
                },
            ],
            "jsonapi": {"version": "1.0"},
            "meta": {"count": 1, "totalPages": 1},
        }

    async def test_filter_invalid_uuid(
        self,
        app: FastAPI,
        client: AsyncClient,
    ):
        resource_type = "custom_uuid_item"

        extra_id = f"{uuid4()}"
        params = {
            "filter[extra_id]": f"{extra_id}" + "z",
        }

        url = app.url_path_for(f"get_{resource_type}_list")
        res = await client.get(url, params=params)
        assert res.status_code >= status.HTTP_400_BAD_REQUEST, res.text

    async def test_filter_none_instead_of_uuid(
        self,
        app: FastAPI,
        client: AsyncClient,
    ):
        resource_type = "custom_uuid_item"

        params = {
            "filter": json.dumps(
                [
                    {
                        "name": "id",
                        "op": "eq",
                        "val": None,
                    },
                ],
            ).decode(),
        }
        url = app.url_path_for(f"get_{resource_type}_list")
        res = await client.get(url, params=params)
        assert res.status_code == status.HTTP_400_BAD_REQUEST, res.text
        assert res.json() == {
            "errors": [
                {
                    "detail": "The field `id` can't be null.",
                    "source": {"parameter": "filters"},
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "title": "Invalid filters querystring parameter.",
                },
            ],
        }

    async def test_join_by_relationships_works_correctly_with_many_filters_for_one_field(
        self,
        app: FastAPI,
        async_session: AsyncSession,
        client: AsyncClient,
        user_1: User,
        user_1_post: PostComment,
    ):
        comment_1 = PostComment(
            text=fake.sentence(),
            post_id=user_1_post.id,
            user_id=user_1.id,
        )
        comment_2 = PostComment(
            text=fake.sentence(),
            post_id=user_1_post.id,
            user_id=user_1.id,
        )
        assert comment_1.text != comment_2.text
        async_session.add_all([comment_1, comment_2])
        await async_session.commit()

        params = {
            "filter": json.dumps(
                [
                    {
                        "name": "posts.comments.text",
                        "op": "eq",
                        "val": comment_1.text,
                    },
                    {
                        "name": "posts.comments.text",
                        "op": "eq",
                        "val": comment_2.text,
                    },
                ],
            ).decode(),
        }

        url = app.url_path_for("get_user_list")
        res = await client.get(url, params=params)
        assert res.status_code == status.HTTP_200_OK, res.text
        assert res.json() == {
            "data": [],
            "jsonapi": {"version": "1.0"},
            "meta": {"count": 0, "totalPages": 1},
        }

    async def test_join_by_relationships_for_one_model_by_different_join_chains(
        self,
        async_session: AsyncSession,
    ):
        app = build_alphabet_app()

        delta_1 = Delta(name="delta_1")
        delta_1.betas = [beta_1 := Beta()]

        gamma_1 = Gamma(delta=delta_1)
        gamma_1.betas = [beta_1]

        delta_2 = Delta(name="delta_2")
        gamma_2 = Gamma(delta=delta_2)

        alpha_1 = Alpha(beta=beta_1, gamma=gamma_2)

        async_session.add_all(
            [
                delta_1,
                delta_2,
                beta_1,
                gamma_1,
                gamma_2,
                alpha_1,
            ],
        )
        await async_session.commit()

        async with AsyncClient(app=app, base_url="http://test") as client:
            params = {
                "filter": json.dumps(
                    [
                        {
                            "name": "beta.gammas.delta.name",
                            "op": "eq",
                            "val": delta_1.name,
                        },
                        {
                            "name": "gamma.delta.name",
                            "op": "eq",
                            "val": delta_2.name,
                        },
                    ],
                ).decode(),
            }

            resource_type = "alpha"
            url = app.url_path_for(f"get_{resource_type}_list")
            response = await client.get(url, params=params)

            assert response.status_code == status.HTTP_200_OK, response.text
            assert response.json() == {
                "data": [{"attributes": {}, "id": f"{alpha_1.id}", "type": "alpha"}],
                "jsonapi": {"version": "1.0"},
                "meta": {"count": 1, "totalPages": 1},
            }

    async def test_relationships_storage_using(
        self,
        clear_relationships_info_storage,
        app: FastAPI,
        client: AsyncClient,
    ):
        params = {
            "filter": json.dumps(
                [
                    {
                        "name": "workplace.name",
                        "op": "eq",
                        "val": "",
                    },
                    {
                        "name": "posts.comments.text",
                        "op": "eq",
                        "val": "",
                    },
                ],
            ).decode(),
        }

        url = app.url_path_for("get_user_list")

        expected_call_count = 3
        expected_relationship_paths = {("workplace",), ("posts", "comments")}
        with mock.patch.object(
            query_building_module,
            "gather_relationships_info",
            wraps=query_building_module.gather_relationships_info,
        ) as mocked_gather:
            response = await client.get(url, params=params)
            actual_relationship_paths = {
                tuple(call_args.kwargs["relationship_path"]) for call_args in mocked_gather.call_args_list
            }

            assert response.status_code == status.HTTP_200_OK, response.text
            assert expected_call_count == mocked_gather.call_count, mocked_gather.mock_calls
            assert expected_relationship_paths == actual_relationship_paths

            # don't gather relationships if already called with these paths
            mocked_gather.reset_mock()
            expected_call_count, expected_relationship_paths = 0, set()
            response = await client.get(url, params=params)
            actual_relationship_paths = {
                tuple(call_args.kwargs["relationship_path"]) for call_args in mocked_gather.call_args_list
            }

            assert response.status_code == status.HTTP_200_OK, response.text
            assert expected_call_count == mocked_gather.call_count, mocked_gather.mock_calls
            assert expected_relationship_paths == actual_relationship_paths

            params = {
                "filter": json.dumps(
                    [
                        {
                            "name": "workplace.name",
                            "op": "eq",
                            "val": "",
                        },
                        # not called for this relationship yet
                        {
                            "name": "bio.birth_city",
                            "op": "eq",
                            "val": "",
                        },
                    ],
                ).decode(),
            }

            # check called for new path only
            mocked_gather.reset_mock()
            expected_call_count, expected_relationship_paths = 1, {("bio",)}
            response = await client.get(url, params=params)
            actual_relationship_paths = {
                tuple(call_args.kwargs["relationship_path"]) for call_args in mocked_gather.call_args_list
            }

            assert response.status_code == status.HTTP_200_OK, response.text
            assert expected_call_count == mocked_gather.call_count, mocked_gather.mock_calls
            assert expected_relationship_paths == actual_relationship_paths


ASCENDING = ""
DESCENDING = "-"


class TestSorts:
    @classmethod
    def get_reverse(cls, order: str) -> bool:
        return order is DESCENDING

    @pytest.mark.parametrize(
        "order",
        [
            pytest.param(ASCENDING, id="ascending"),
            pytest.param(DESCENDING, id="descending"),
        ],
    )
    async def test_sort(
        self,
        app: FastAPI,
        client: AsyncClient,
        async_session: AsyncSession,
        order: str,
    ):
        user_1, _, user_3 = (
            await create_user(async_session, age=10),
            await create_user(async_session),
            await create_user(async_session, age=15),
        )

        params = {
            "filter": json.dumps(
                [
                    {
                        "name": "id",
                        "op": "in",
                        "val": [
                            user_1.id,
                            user_3.id,
                        ],
                    },
                ],
            ).decode(),
            "sort": f"{order}age",
        }
        url = app.url_path_for("get_user_list")
        res = await client.get(url, params=params)
        assert res.status_code == status.HTTP_200_OK, res.text
        assert res.json() == {
            "data": sorted(
                [
                    {
                        "attributes": UserAttributesBaseSchema.model_validate(user_1).model_dump(),
                        "id": f"{user_1.id}",
                        "type": "user",
                    },
                    {
                        "attributes": UserAttributesBaseSchema.model_validate(user_3).model_dump(),
                        "id": f"{user_3.id}",
                        "type": "user",
                    },
                ],
                key=lambda x: x["attributes"]["age"],
                reverse=self.get_reverse(order),
            ),
            "jsonapi": {"version": "1.0"},
            "meta": {"count": 2, "totalPages": 1},
        }

    @pytest.mark.parametrize(
        "age_order, movie_order, comp_order, user_1, user_2, user_3, expected_order",
        [
            pytest.param(
                ASCENDING,
                ASCENDING,
                ASCENDING,
                [10, "AAA", "COMP_1"],
                [15, "BBB", "COMP_2"],
                [20, "CCC", "COMP_3"],
                ["user_1", "user_2", "user_3"],
                id="ascending_simple",
            ),
            pytest.param(
                DESCENDING,
                DESCENDING,
                DESCENDING,
                [10, "AAA", "COMP_1"],
                [15, "BBB", "COMP_2"],
                [20, "CCC", "COMP_3"],
                ["user_3", "user_2", "user_1"],
                id="descending_simple",
            ),
            pytest.param(
                ASCENDING,
                ASCENDING,
                ASCENDING,
                [10, "AAA", "COMP_3"],
                [15, "CCC", "COMP_2"],
                [15, "BBB", "COMP_1"],
                ["user_1", "user_3", "user_2"],
                id="ascending_be_second_condition",
            ),
            pytest.param(
                ASCENDING,
                DESCENDING,
                ASCENDING,
                [10, "AAA", "COMP_3"],
                [15, "BBB", "COMP_2"],
                [15, "CCC", "COMP_1"],
                ["user_1", "user_3", "user_2"],
                id="descending_be_second_condition",
            ),
            pytest.param(
                ASCENDING,
                DESCENDING,
                DESCENDING,
                [10, "AAA", "COMP_3"],
                [10, "AAA", "COMP_2"],
                [10, "BBB", "COMP_1"],
                ["user_3", "user_1", "user_2"],
                id="last_condition",
            ),
        ],
    )
    async def test_sorts_by_relationships(
        self,
        app: FastAPI,
        client: AsyncClient,
        async_session: AsyncSession,
        age_order: str,
        movie_order: str,
        comp_order: str,
        user_1: list[int, str],
        user_2: list[int, str],
        user_3: list[int, str],
        expected_order: list[Literal["user_1", "user_2", "user_3"]],
    ):
        age, movie_1, computer_name = user_1
        user_1 = await create_user(async_session, age=age)
        await create_user_bio(async_session, user_1, favourite_movies=movie_1)
        await create_computer(async_session, name=computer_name, user=user_1)

        age, movie_2, computer_name = user_2
        user_2 = await create_user(async_session, age=age)
        await create_user_bio(async_session, user_2, favourite_movies=movie_2)
        await create_computer(async_session, name=computer_name, user=user_2)

        age, movie_3, computer_name = user_3
        user_3 = await create_user(async_session, age=age)
        await create_user_bio(async_session, user_3, favourite_movies=movie_3)
        await create_computer(async_session, name=computer_name, user=user_3)

        user_map = {
            "user_1": user_1,
            "user_2": user_2,
            "user_3": user_3,
        }

        params = {
            "filter": json.dumps(
                [
                    # Note: hit filters to ensure there are no conflicts between sort and filter joins
                    {"name": "bio.favourite_movies", "op": "in", "val": [movie_1, movie_2, movie_3]},
                ],
            ).decode(),
            "sort": f"{age_order}age,{movie_order}bio.favourite_movies,{comp_order}computers.name",
        }
        url = app.url_path_for("get_user_list")
        response = await client.get(url, params=params)
        assert response.status_code == status.HTTP_200_OK, response.text

        response_json = response.json()
        assert response_json
        assert response_json["meta"] == {"count": 3, "totalPages": 1}
        assert response_json["data"] == [
            {
                "id": f"{user_map[user].id}",
                "attributes": UserAttributesBaseSchema.model_validate(user_map[user]).model_dump(),
                "type": "user",
            }
            for user in expected_order
        ]

    @pytest.mark.parametrize(
        "order, boris_position",
        [
            (ASCENDING, -1),
            (DESCENDING, 0),
        ],
    )
    async def test_register_free_sort(
        self,
        async_session: AsyncSession,
        order: str,
        boris_position: int,
    ):
        resource_type = "test_register_free_sort"

        # lexicographic order: Anton, Boris, anton
        await create_user(async_session, name="Anton")
        await create_user(async_session, name="anton")
        target_user = await create_user(async_session, name="Boris")

        class UserWithNameFieldSortingSchema(UserAttributesBaseSchema):
            name: Annotated[str, sql_register_free_sort]

        app = build_app_custom(
            model=User,
            schema=UserWithNameFieldSortingSchema,
            resource_type=resource_type,
        )
        params = {"sort": f"{order}name"}
        url = app.url_path_for(f"get_{resource_type}_list")

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(url, params=params)
            assert response.status_code == status.HTTP_200_OK, response.text
            response_json = response.json()

        expected_count = 3
        assert len(response_json["data"]) == expected_count
        assert response_json["data"][boris_position] == {
            "id": f"{target_user.id}",
            "attributes": UserWithNameFieldSortingSchema.model_validate(target_user).model_dump(),
            "type": resource_type,
        }


class TestFilteringErrors:
    async def test_incorrect_field_name(
        self,
        app: FastAPI,
        client: AsyncClient,
    ):
        url = app.url_path_for("get_user_list")
        params = {
            "filter": json.dumps(
                [
                    {
                        "name": "fake_field_name",
                        "op": "eq",
                        "val": "",
                    },
                ],
            ).decode(),
        }
        response = await client.get(url, params=params)
        assert response.status_code == status.HTTP_400_BAD_REQUEST, response.text
        assert response.json() == {
            "errors": [
                {
                    "detail": "UserSchema has no attribute fake_field_name",
                    "source": {"parameter": "filters"},
                    "status_code": 400,
                    "title": "Invalid filters querystring parameter.",
                },
            ],
        }


# todo: test errors
