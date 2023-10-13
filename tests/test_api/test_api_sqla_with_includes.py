import logging
from copy import deepcopy
from itertools import chain, zip_longest
from json import dumps
from typing import Dict, List, Optional, Type
from uuid import UUID, uuid4

from fastapi import FastAPI, status
from httpx import AsyncClient
from pydantic import BaseModel, Field, root_validator, validator
from pytest import fixture, mark, param  # noqa PT013
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_jsonapi import RoutersJSONAPI
from fastapi_jsonapi.exceptions import BadRequest
from fastapi_jsonapi.schema_builder import SchemaBuilder
from fastapi_jsonapi.views.view_base import ViewBase
from tests.fixtures.app import build_app_custom
from tests.fixtures.entities import build_workplace, create_user
from tests.misc.utils import fake
from tests.models import (
    Computer,
    IdCast,
    Post,
    PostComment,
    SelfRelationship,
    User,
    UserBio,
    Workplace,
)
from tests.schemas import (
    CustomUserAttributesSchema,
    IdCastSchema,
    PostAttributesBaseSchema,
    PostCommentAttributesBaseSchema,
    SelfRelationshipSchema,
    UserAttributesBaseSchema,
    UserBioAttributesBaseSchema,
    UserInSchemaAllowIdOnPost,
    UserPatchSchema,
    UserSchema,
)

pytestmark = mark.asyncio

logging.basicConfig(level=logging.DEBUG)


def association_key(data: dict):
    return data["type"], data["id"]


async def test_root(client: AsyncClient):
    response = await client.get("/docs")
    assert response.status_code == status.HTTP_200_OK


async def test_get_users(app: FastAPI, client: AsyncClient, user_1: User, user_2: User):
    url = app.url_path_for("get_user_list")
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
    assert response_data["data"]["id"] == ViewBase.get_db_item_id(user_1)
    assert response_data["data"]["type"] == "user"
    assert "included" in response_data, response_data
    included_bio = response_data["included"][0]
    assert included_bio["id"] == ViewBase.get_db_item_id(user_1_bio)
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
        assert user_data["id"] == ViewBase.get_db_item_id(user)
        assert user_data["type"] == "user"

    assert "included" in response_data, response_data
    included_bio = response_data["included"][0]
    assert included_bio["id"] == ViewBase.get_db_item_id(user_1_bio)
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
        assert response_data == {
            "data": [
                {
                    "attributes": UserAttributesBaseSchema.from_orm(user),
                    "id": str(user.id),
                    "type": "user",
                },
            ],
            "jsonapi": {"version": "1.0"},
            "meta": {"count": 2, "totalPages": 2},
        }


class TestCreatePostAndComments:
    async def test_get_posts_with_users(
        self,
        app: FastAPI,
        client: AsyncClient,
        user_1: User,
        user_2: User,
        user_1_posts: List[Post],
        user_2_posts: List[Post],
    ):
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
        ).dict()
        post_create = {
            "data": {
                "attributes": post_attributes,
                "relationships": {
                    "user": {
                        "data": {
                            "type": "user",
                            "id": user_1.id,
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
                        "id": str(user_1.id),
                    },
                },
            },
        }
        included = response_data["included"]
        assert included == [
            {
                "id": str(user_1.id),
                "type": "user",
                "attributes": UserAttributesBaseSchema.from_orm(user_1).dict(),
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
        url = app.url_path_for("get_comment_list")
        url = f"{url}?include=author,post,post.user"
        comment_attributes = PostCommentAttributesBaseSchema(
            text=fake.sentence(),
        ).dict()
        comment_create = {
            "data": {
                "attributes": comment_attributes,
                "relationships": {
                    "post": {
                        "data": {
                            "type": "post",
                            "id": user_1_post.id,
                        },
                    },
                    "author": {
                        "data": {
                            "type": "user",
                            "id": user_2.id,
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
            "type": "comment",
            "attributes": comment_attributes,
            "relationships": {
                "post": {
                    "data": {
                        "type": "post",
                        "id": str(user_1_post.id),
                    },
                },
                "author": {
                    "data": {
                        "type": "user",
                        "id": str(user_2.id),
                    },
                },
            },
        }
        included = response_data["included"]
        assert included == [
            {
                "type": "post",
                "id": str(user_1_post.id),
                "attributes": PostAttributesBaseSchema.from_orm(user_1_post).dict(),
                "relationships": {
                    "user": {
                        "data": {
                            "id": str(user_1.id),
                            "type": "user",
                        },
                    },
                },
            },
            {
                "type": "user",
                "id": str(user_1.id),
                "attributes": UserAttributesBaseSchema.from_orm(user_1).dict(),
            },
            {
                "type": "user",
                "id": str(user_2.id),
                "attributes": UserAttributesBaseSchema.from_orm(user_2).dict(),
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
        url = app.url_path_for("get_comment_list")
        comment_attributes = PostCommentAttributesBaseSchema(
            text=fake.sentence(),
        ).dict()
        comment_create = {
            "data": {
                "attributes": comment_attributes,
                "relationships": {
                    "post": {
                        "data": {
                            "type": "post",
                            "id": user_1_post.id,
                        },
                    },
                    # don't pass "author"
                },
            },
        }
        response = await client.post(url, json=comment_create)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, response.text
        response_data = response.json()
        assert response_data == {
            "detail": [
                {
                    "loc": [
                        "body",
                        "data",
                        "relationships",
                        "author",
                    ],
                    "msg": "field required",
                    "type": "value_error.missing",
                },
            ],
        }

    async def test_create_comment_error_no_relationships_content(
        self,
        app: FastAPI,
        client: AsyncClient,
    ):
        url = app.url_path_for("get_comment_list")
        comment_attributes = PostCommentAttributesBaseSchema(
            text=fake.sentence(),
        ).dict()
        comment_create = {
            "data": {
                "attributes": comment_attributes,
                "relationships": {
                    # don't pass "post"
                    # don't pass "author"
                },
            },
        }
        response = await client.post(url, json=comment_create)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, response.text
        response_data = response.json()
        assert response_data == {
            "detail": [
                {
                    "loc": [
                        "body",
                        "data",
                        "relationships",
                        "post",
                    ],
                    "msg": "field required",
                    "type": "value_error.missing",
                },
                {
                    "loc": [
                        "body",
                        "data",
                        "relationships",
                        "author",
                    ],
                    "msg": "field required",
                    "type": "value_error.missing",
                },
            ],
        }

    async def test_create_comment_error_no_relationships_field(
        self,
        app: FastAPI,
        client: AsyncClient,
    ):
        url = app.url_path_for("get_comment_list")
        comment_attributes = PostCommentAttributesBaseSchema(
            text=fake.sentence(),
        ).dict()
        comment_create = {
            "data": {
                "attributes": comment_attributes,
                # don't pass "relationships" at all
            },
        }
        response = await client.post(url, json=comment_create)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, response.text
        response_data = response.json()
        assert response_data == {
            "detail": [
                {
                    "loc": [
                        "body",
                        "data",
                        "relationships",
                    ],
                    "msg": "field required",
                    "type": "value_error.missing",
                },
            ],
        }


async def test_get_users_with_all_inner_relations(
    app: FastAPI,
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
    url = app.url_path_for("get_user_list")
    url = f"{url}?include=bio,posts,posts.comments,posts.comments.author"
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
    assert user_data["id"] == str(user_1.id)
    assert user_data["attributes"] == UserAttributesBaseSchema.from_orm(user_1)


async def test_get_user_not_found(app: FastAPI, client: AsyncClient):
    fake_id = fake.pyint()
    url = app.url_path_for("get_user_detail", obj_id=fake_id)
    res = await client.get(url)

    assert res.json() == {
        "errors": [
            {
                "detail": f"Resource User `{fake_id}` not found",
                "title": "Resource not found.",
                "status_code": status.HTTP_404_NOT_FOUND,
                "meta": {"parameter": "id"},
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
                ).dict(),
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
                    keys_to_ids_list={"foobar": [1, 2, 3], "spameggs": [2, 3, 4]},
                ).dict(),
                "relationships": {"user": {"data": {"type": "user", "id": user_1.id}}},
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
        assert included_user["id"] == str(user_1.id)
        assert included_user["attributes"] == UserAttributesBaseSchema.from_orm(user_1)

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
                ).dict(),
                "relationships": {
                    "computers": {
                        "data": [
                            {
                                "id": computer_1.id,
                                "type": "computer",
                            },
                            {
                                "id": computer_2.id,
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
                                "id": str(computer_1.id),
                                "type": "computer",
                            },
                            {
                                "id": str(computer_2.id),
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
                    "id": str(computer_1.id),
                    "type": "computer",
                },
                {
                    "attributes": {"name": computer_2.name},
                    "id": str(computer_2.id),
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
                ).dict(),
                "relationships": {
                    "computers": {
                        "data": [
                            {
                                "id": computer_1.id,
                                "type": "computer",
                            },
                            {
                                "id": computer_2.id,
                                "type": "computer",
                            },
                        ],
                    },
                    "workplace": {
                        "data": {
                            "id": str(workplace_1.id),
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
                                "id": str(computer_1.id),
                                "type": "computer",
                            },
                            {
                                "id": str(computer_2.id),
                                "type": "computer",
                            },
                        ],
                    },
                    "workplace": {
                        "data": {
                            "id": str(workplace_1.id),
                            "type": "workplace",
                        },
                    },
                },
                "type": "user",
            },
            "included": [
                {
                    "attributes": {"name": computer_1.name},
                    "id": str(computer_1.id),
                    "type": "computer",
                },
                {
                    "attributes": {"name": computer_2.name},
                    "id": str(computer_2.id),
                    "type": "computer",
                },
                {
                    "attributes": {"name": workplace_1.name},
                    "id": str(workplace_1.id),
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
                ).dict(),
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
                ).dict(),
            },
        }
        app.url_path_for("get_user_list")
        res = await client.post("/users", json=create_user_body)
        assert res.status_code == status.HTTP_201_CREATED, res.text
        response_data = res.json()
        assert "data" in response_data, response_data
        assert response_data["data"]["attributes"] == create_user_body["data"]["attributes"]

        user_id = response_data["data"]["id"]

        res = await client.get(f"/users/{user_id}")
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

        new_id = str(fake.pyint(100, 999))
        attrs = UserAttributesBaseSchema(
            name=fake.name(),
            age=fake.pyint(),
            email=fake.email(),
        )
        create_user_body = {
            "data": {
                "attributes": attrs.dict(),
                "id": new_id,
            },
        }

        async with AsyncClient(app=app, base_url="http://test") as client:
            url = app.url_path_for(f"get_{resource_type}_list")
            res = await client.post(url, json=create_user_body)
            assert res.status_code == status.HTTP_201_CREATED, res.text
            assert res.json() == {
                "data": {
                    "attributes": attrs.dict(),
                    "id": new_id,
                    "type": resource_type,
                },
                "jsonapi": {"version": "1.0"},
                "meta": None,
            }

    async def test_create_id_by_client_uuid_type(self):
        resource_type = fake.word()
        app = build_app_custom(
            model=IdCast,
            schema=IdCastSchema,
            resource_type=resource_type,
        )

        new_id = str(uuid4())
        create_body = {
            "data": {
                "attributes": {},
                "id": new_id,
            },
        }

        async with AsyncClient(app=app, base_url="http://test") as client:
            url = app.url_path_for(f"get_{resource_type}_list")
            res = await client.post(url, json=create_body)
            assert res.status_code == status.HTTP_201_CREATED, res.text
            assert res.json() == {
                "data": {
                    "attributes": {},
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
            schema=SelfRelationshipSchema,
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
            assert (parent_object_id := response_json["data"].get("id"))
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
                        "self_relationship": {
                            "data": {
                                "type": resource_type,
                                "id": parent_object_id,
                            },
                        },
                    },
                },
            }
            url = f"{url}?include=self_relationship"
            res = await client.post(url, json=create_with_relationship_body)
            assert res.status_code == status.HTTP_201_CREATED, res.text

            response_json = res.json()
            assert response_json["data"]
            assert (child_object_id := response_json["data"].get("id"))
            assert res.json() == {
                "data": {
                    "attributes": {"name": "child"},
                    "id": child_object_id,
                    "relationships": {
                        "self_relationship": {
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
                        "attributes": {"name": "parent"},
                        "id": parent_object_id,
                        "type": "self_relationship",
                    },
                ],
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
        ).dict()

        patch_user_body = {
            "data": {
                "id": user_1.id,
                "attributes": new_attrs,
            },
        }
        url = app.url_path_for("get_user_detail", obj_id=user_1.id)
        res = await client.patch(url, json=patch_user_body)
        assert res.status_code == status.HTTP_200_OK, res.text

        assert res.json() == {
            "data": {
                "attributes": new_attrs,
                "id": str(user_1.id),
                "type": "user",
            },
            "jsonapi": {"version": "1.0"},
            "meta": None,
        }

    async def test_do_nothing_with_field_not_presented_in_model(
        self,
        user_1: User,
    ):
        class UserPatchSchemaWithExtraAttribute(UserPatchSchema):
            attr_which_is_not_presented_in_model: str

        resource_type = "user_custom_a"
        app = build_app_custom(
            model=User,
            schema=UserSchema,
            schema_in_post=UserPatchSchemaWithExtraAttribute,
            schema_in_patch=UserPatchSchemaWithExtraAttribute,
            resource_type=resource_type,
        )
        new_attrs = UserPatchSchemaWithExtraAttribute(
            name=fake.name(),
            age=fake.pyint(),
            email=fake.email(),
            attr_which_is_not_presented_in_model=fake.name(),
        ).dict()

        patch_user_body = {
            "data": {
                "id": user_1.id,
                "attributes": new_attrs,
            },
        }
        async with AsyncClient(app=app, base_url="http://test") as client:
            url = app.url_path_for(f"update_{resource_type}_detail", obj_id=user_1.id)
            res = await client.patch(url, json=patch_user_body)
            assert res.status_code == status.HTTP_200_OK, res.text

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
                "attributes": new_attributes.dict(),
                "id": user_1.id,
            },
        }

        async with AsyncClient(app=app, base_url="http://test") as client:
            url = app.url_path_for(f"update_{resource_type}_detail", obj_id=user_1.id)
            res = await client.patch(url, json=create_body)

        assert res.status_code == status.HTTP_200_OK, res.text
        assert res.json() == {
            "data": {
                "attributes": UserAttributesBaseSchema(**new_attributes.dict()).dict(),
                "id": str(user_1.id),
                "type": resource_type,
            },
            "jsonapi": {"version": "1.0"},
            "meta": None,
        }

        messages = [x.message for x in caplog.get_records("call") if x.levelno == logging.WARNING]
        messages.sort()
        for log_message, expected in zip_longest(
            messages,
            sorted([f"No field {name!r}" for name in ("spam", "eggs")]),
        ):
            assert expected in log_message


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
        ).dict()

        patch_user_body = {
            "data": {
                "id": user_1.id,
                "attributes": new_attrs,
                "relationships": {
                    "workplace": {
                        "data": {
                            "type": "workplace",
                            "id": workplace_1.id,
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
                "id": str(user_1.id),
                "relationships": {
                    "workplace": {
                        "data": {
                            "type": "workplace",
                            "id": str(workplace_1.id),
                        },
                    },
                },
                "type": "user",
            },
            "included": [
                {
                    "attributes": {"name": workplace_1.name},
                    "id": str(workplace_1.id),
                    "type": "workplace",
                },
            ],
            "jsonapi": {"version": "1.0"},
            "meta": None,
        }

        patch_user_body["data"]["relationships"]["workplace"]["data"]["id"] = workplace_2.id

        # update relationship with patch endpoint
        res = await client.patch(url, json=patch_user_body)
        assert res.status_code == status.HTTP_200_OK, res.text

        assert res.json() == {
            "data": {
                "attributes": new_attrs,
                "id": str(user_1.id),
                "relationships": {
                    "workplace": {
                        "data": {
                            "type": "workplace",
                            "id": str(workplace_2.id),
                        },
                    },
                },
                "type": "user",
            },
            "included": [
                {
                    "attributes": {"name": workplace_2.name},
                    "id": str(workplace_2.id),
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
                "id": user_1_bio.id,
                "attributes": UserBioAttributesBaseSchema.from_orm(user_1_bio).dict(),
                "relationships": {
                    "user": {
                        "data": {
                            "type": "user",
                            "id": user_2.id,
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
                    "detail": "Object update error",
                    "source": {"pointer": "/data"},
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "title": "Bad Request",
                    "meta": {
                        "id": str(user_1_bio.id),
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
        ).dict()

        fake_relationship_id = "1"
        patch_user_body = {
            "data": {
                "id": user_1.id,
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
                    "detail": f"Workplace.id: {fake_relationship_id} not found",
                    "source": {"pointer": ""},
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
        user_id = user_1.id
        another_id = 0
        patch_user_body = {
            "data": {
                "id": user_id,
                "attributes": UserAttributesBaseSchema.from_orm(user_1).dict(),
            },
        }

        url = app.url_path_for("get_user_detail", obj_id=another_id)
        res = await client.patch(url, json=patch_user_body)
        assert res.status_code == status.HTTP_400_BAD_REQUEST, res.text
        assert res.json() == {
            "errors": [
                {
                    "detail": "obj_id and data.id should be same",
                    "source": {"pointer": "/data/id"},
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "title": "Bad Request",
                },
            ],
        }


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
        ).dict()

        patch_user_body = {
            "data": {
                "id": user_1.id,
                "attributes": new_attrs,
                "relationships": {
                    "computers": {
                        "data": [
                            {
                                "type": "computer",
                                # test id as int
                                "id": computer_1.id,
                            },
                            {
                                "type": "computer",
                                # test id as str
                                "id": str(computer_2.id),
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
                "id": str(user_1.id),
                "relationships": {
                    "computers": {
                        "data": [
                            {
                                "type": "computer",
                                "id": str(computer_1.id),
                            },
                            {
                                "type": "computer",
                                "id": str(computer_2.id),
                            },
                        ],
                    },
                },
                "type": "user",
            },
            "included": [
                {
                    "attributes": {"name": computer_1.name},
                    "id": str(computer_1.id),
                    "type": "computer",
                },
                {
                    "attributes": {"name": computer_2.name},
                    "id": str(computer_2.id),
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
                    "id": str(computer_1.id),
                },
            ],
        }

        # update relationships with patch endpoint
        res = await client.patch(url, json=patch_user_body)
        assert res.status_code == status.HTTP_200_OK, res.text

        assert res.json() == {
            "data": {
                "attributes": new_attrs,
                "id": str(user_1.id),
                "relationships": {
                    "computers": {
                        "data": [
                            {
                                "type": "computer",
                                "id": str(computer_1.id),
                            },
                        ],
                    },
                },
                "type": "user",
            },
            "included": [
                {
                    "attributes": {"name": computer_1.name},
                    "id": str(computer_1.id),
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
        ).dict()

        fake_computer_id = fake.pyint(min_value=1000, max_value=9999)
        assert fake_computer_id != computer_2.id

        patch_user_body = {
            "data": {
                "id": user_1.id,
                "attributes": new_attrs,
                "relationships": {
                    "computers": {
                        "data": [
                            {
                                "type": "computer",
                                "id": str(computer_1.id),
                            },
                            {
                                "type": "computer",
                                "id": fake_computer_id,
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
                    "detail": "Objects for Computer with ids: {" + str(fake_computer_id) + "} not found",
                    "source": {"pointer": "/data"},
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "title": "Related object not found.",
                },
            ],
        }


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
            "filter": dumps(
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
            ),
        }

        url = app.url_path_for("get_user_list")
        res = await client.delete(url, params=params)
        assert res.status_code == status.HTTP_200_OK, res.text
        assert res.json() == {
            "data": [
                {
                    "attributes": UserAttributesBaseSchema.from_orm(user_1),
                    "id": str(user_1.id),
                    "type": "user",
                },
                {
                    "attributes": UserAttributesBaseSchema.from_orm(user_3),
                    "id": str(user_3.id),
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
                    "attributes": UserAttributesBaseSchema.from_orm(user_2),
                    "id": str(user_2.id),
                    "type": "user",
                },
            ],
            "jsonapi": {"version": "1.0"},
            "meta": {"count": 1, "totalPages": 1},
        }


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
            id: UUID = Field(client_can_set_id=True)

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
        res = await client.get("/users", params=params)
        assert res.status_code == status.HTTP_200_OK, res.text
        assert res.json() == {
            "data": [],
            "jsonapi": {"version": "1.0"},
            "meta": {"count": 0, "totalPages": 1},
        }

    @mark.parametrize("field_name", [param(name, id=name) for name in ["id", "name", "age", "email"]])
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
                    "attributes": UserAttributesBaseSchema.from_orm(user_1).dict(),
                    "id": str(user_1.id),
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
                    "attributes": UserAttributesBaseSchema.from_orm(user_1).dict(),
                    "id": str(user_1.id),
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

    async def test_composite_filter_by_one_field(
        self,
        app: FastAPI,
        client: AsyncClient,
        user_1: User,
        user_2: User,
        user_3: User,
    ):
        params = {
            "filter": dumps(
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
            ),
        }

        url = app.url_path_for("get_user_list")
        res = await client.get(url, params=params)
        assert res.status_code == status.HTTP_200_OK, res.text
        assert res.json() == {
            "data": [
                {
                    "attributes": UserAttributesBaseSchema.from_orm(user_1),
                    "id": str(user_1.id),
                    "type": "user",
                },
                {
                    "attributes": UserAttributesBaseSchema.from_orm(user_3),
                    "id": str(user_3.id),
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
            "filter": dumps(
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
            ),
        }

        url = app.url_path_for("get_user_list")
        res = await client.get(url, params=params)
        assert res.status_code == status.HTTP_200_OK, res.text
        assert res.json() == {
            "data": [
                {
                    "attributes": UserAttributesBaseSchema.from_orm(user_1),
                    "id": str(user_1.id),
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
            "filter": dumps(
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
                        "val": user_2.id,
                    },
                ],
            ),
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
            await build_workplace(async_session, name=workplace_name),
            await build_workplace(async_session, name=workplace_name),
            await build_workplace(async_session, name=workplace_name),
            await build_workplace(async_session, name=workplace_name),
        )

        user_1, user_2, _, user_4 = (
            await create_user(async_session, name="John Doe", age=20, workplace=workplace_1),
            await create_user(async_session, name="Jane Doe", age=25, workplace=workplace_2),
            await create_user(async_session, name="Jonny Doe", age=30, workplace=workplace_3),
            await create_user(async_session, name="Mary Jane", age=21, workplace=workplace_4),
        )

        params = {
            "filter": dumps(
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
            ),
        }

        url = app.url_path_for("get_user_list")
        res = await client.get(url, params=params)
        assert res.status_code == status.HTTP_200_OK, res.text
        assert res.json() == {
            "data": [
                {
                    "attributes": UserAttributesBaseSchema.from_orm(user_1),
                    "id": str(user_1.id),
                    "type": "user",
                },
                {
                    "attributes": UserAttributesBaseSchema.from_orm(user_2),
                    "id": str(user_2.id),
                    "type": "user",
                },
                {
                    "attributes": UserAttributesBaseSchema.from_orm(user_4),
                    "id": str(user_4.id),
                    "type": "user",
                },
            ],
            "jsonapi": {"version": "1.0"},
            "meta": {"count": 3, "totalPages": 1},
        }


ASCENDING = ""
DESCENDING = "-"


class TestSorts:
    def get_reverse(self, order: str) -> bool:
        return order is DESCENDING

    @mark.parametrize(
        "order",
        [
            param(ASCENDING, id="ascending"),
            param(DESCENDING, id="descending"),
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
            "filter": dumps(
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
            ),
            "sort": f"{order}age",
        }
        url = app.url_path_for("get_user_list")
        res = await client.get(url, params=params)
        assert res.status_code == status.HTTP_200_OK, res.text
        assert res.json() == {
            "data": sorted(
                [
                    {
                        "attributes": UserAttributesBaseSchema.from_orm(user_1).dict(),
                        "id": str(user_1.id),
                        "type": "user",
                    },
                    {
                        "attributes": UserAttributesBaseSchema.from_orm(user_3).dict(),
                        "id": str(user_3.id),
                        "type": "user",
                    },
                ],
                key=lambda x: x["attributes"]["age"],
                reverse=self.get_reverse(order),
            ),
            "jsonapi": {"version": "1.0"},
            "meta": {"count": 2, "totalPages": 1},
        }


class TestValidators:
    resource_type = "validator"

    @fixture(autouse=True)
    def _refresh_caches(self) -> None:
        object_schemas_cache = deepcopy(SchemaBuilder.object_schemas_cache)
        relationship_schema_cache = deepcopy(SchemaBuilder.relationship_schema_cache)
        base_jsonapi_object_schemas_cache = deepcopy(SchemaBuilder.base_jsonapi_object_schemas_cache)

        all_jsonapi_routers = deepcopy(RoutersJSONAPI.all_jsonapi_routers)

        yield

        SchemaBuilder.object_schemas_cache = object_schemas_cache
        SchemaBuilder.relationship_schema_cache = relationship_schema_cache
        SchemaBuilder.base_jsonapi_object_schemas_cache = base_jsonapi_object_schemas_cache

        RoutersJSONAPI.all_jsonapi_routers = all_jsonapi_routers

    def build_app(self, schema, resource_type: Optional[str] = None) -> FastAPI:
        return build_app_custom(
            model=User,
            schema=schema,
            # schema_in_post=schema,
            # schema_in_patch=schema,
            resource_type=resource_type or self.resource_type,
        )

    def inherit(self, schema: Type[BaseModel]) -> Type[BaseModel]:
        class InheritedSchema(schema):
            pass

        return InheritedSchema

    async def execute_request_and_check_response(
        self,
        app: FastAPI,
        body: Dict,
        expected_detail: str,
        resource_type: Optional[str] = None,
    ):
        resource_type = resource_type or self.resource_type
        async with AsyncClient(app=app, base_url="http://test") as client:
            url = app.url_path_for(f"get_{resource_type}_list")
            res = await client.post(url, json=body)
            assert res.status_code == status.HTTP_400_BAD_REQUEST, res.text
            assert res.json() == {
                "detail": {
                    "errors": [
                        {
                            "detail": expected_detail,
                            "source": {"pointer": ""},
                            "status_code": status.HTTP_400_BAD_REQUEST,
                            "title": "Bad Request",
                        },
                    ],
                },
            }

    async def execute_request_twice_and_check_response(
        self,
        schema: Type[BaseModel],
        body: Dict,
        expected_detail: str,
    ):
        """
        Makes two requests for check schema inheritance
        """
        resource_type_1 = self.resource_type + fake.word()
        app_1 = self.build_app(schema, resource_type=resource_type_1)
        resource_type_2 = self.resource_type + fake.word()
        app_2 = self.build_app(self.inherit(schema), resource_type=resource_type_2)

        for app, resource_type in [(app_1, resource_type_1), (app_2, resource_type_2)]:
            await self.execute_request_and_check_response(
                app=app,
                body=body,
                expected_detail=expected_detail,
                resource_type=resource_type,
            )

    async def test_field_validator_call(self):
        """
        Basic check to ensure that field validator called
        """

        class UserSchemaWithValidator(BaseModel):
            name: str

            @validator("name")
            def validate_name(cls, v):
                # checks that cls arg is not bound to the origin class
                assert cls is not UserSchemaWithValidator

                raise BadRequest(detail="Check validator")

            class Config:
                orm_mode = True

        attrs = {"name": fake.name()}
        create_user_body = {"data": {"attributes": attrs}}

        await self.execute_request_twice_and_check_response(
            schema=UserSchemaWithValidator,
            body=create_user_body,
            expected_detail="Check validator",
        )

    async def test_field_validator_each_item_arg(self):
        class UserSchemaWithValidator(BaseModel):
            names: List[str]

            @validator("names", each_item=True)
            def validate_name(cls, v):
                if v == "bad_name":
                    raise BadRequest(detail="Bad name not allowed")

            class Config:
                orm_mode = True

        attrs = {"names": ["good_name", "bad_name"]}
        create_user_body = {"data": {"attributes": attrs}}

        await self.execute_request_twice_and_check_response(
            schema=UserSchemaWithValidator,
            body=create_user_body,
            expected_detail="Bad name not allowed",
        )

    async def test_field_validator_pre_arg(self):
        class UserSchemaWithValidator(BaseModel):
            name: List[str]

            @validator("name", pre=True)
            def validate_name_pre(cls, v):
                raise BadRequest(detail="Pre validator called")

            @validator("name")
            def validate_name(cls, v):
                raise BadRequest(detail="Not pre validator called")

            class Config:
                orm_mode = True

        attrs = {"name": fake.name()}
        create_user_body = {"data": {"attributes": attrs}}

        await self.execute_request_twice_and_check_response(
            schema=UserSchemaWithValidator,
            body=create_user_body,
            expected_detail="Pre validator called",
        )

    async def test_field_validator_always_arg(self):
        class UserSchemaWithValidator(BaseModel):
            name: str = None

            @validator("name", always=True)
            def validate_name(cls, v):
                raise BadRequest(detail="Called always validator")

            class Config:
                orm_mode = True

        create_user_body = {"data": {"attributes": {}}}

        await self.execute_request_twice_and_check_response(
            schema=UserSchemaWithValidator,
            body=create_user_body,
            expected_detail="Called always validator",
        )

    async def test_field_validator_several_validators(self):
        class UserSchemaWithValidator(BaseModel):
            field: str

            @validator("field")
            def validator_1(cls, v):
                if v == "check_validator_1":
                    raise BadRequest(detail="Called validator 1")

                return v

            @validator("field")
            def validator_2(cls, v):
                if v == "check_validator_2":
                    raise BadRequest(detail="Called validator 2")

                return v

            class Config:
                orm_mode = True

        attrs = {"field": "check_validator_1"}
        create_user_body = {"data": {"attributes": attrs}}

        app = self.build_app(UserSchemaWithValidator)
        await self.execute_request_and_check_response(
            app=app,
            body=create_user_body,
            expected_detail="Called validator 1",
        )

        attrs = {"field": "check_validator_2"}
        create_user_body = {"data": {"attributes": attrs}}

        await self.execute_request_and_check_response(
            app=app,
            body=create_user_body,
            expected_detail="Called validator 2",
        )

    async def test_field_validator_asterisk(self):
        class UserSchemaWithValidator(BaseModel):
            field_1: str
            field_2: str

            @validator("*", pre=True)
            def validator(cls, v):
                if v == "bad_value":
                    raise BadRequest(detail="Check validator")

            class Config:
                orm_mode = True

        attrs = {
            "field_1": "bad_value",
            "field_2": "",
        }
        create_user_body = {"data": {"attributes": attrs}}

        app = self.build_app(UserSchemaWithValidator)
        await self.execute_request_and_check_response(
            app=app,
            body=create_user_body,
            expected_detail="Check validator",
        )

        attrs = {
            "field_1": "",
            "field_2": "bad_value",
        }
        create_user_body = {"data": {"attributes": attrs}}

        await self.execute_request_and_check_response(
            app=app,
            body=create_user_body,
            expected_detail="Check validator",
        )

    async def test_check_validator_for_id_field(self):
        """
        Unusual case because of "id" field handling in
        a different way than attributes
        """

        class UserSchemaWithValidator(BaseModel):
            id: int = Field(client_can_set_id=True)

            @validator("id")
            def validate_id(cls, v):
                raise BadRequest(detail="Check validator")

            class Config:
                orm_mode = True

        create_user_body = {
            "data": {
                "attributes": {},
                "id": 42,
            },
        }

        await self.execute_request_twice_and_check_response(
            schema=UserSchemaWithValidator,
            body=create_user_body,
            expected_detail="Check validator",
        )

    @mark.parametrize(
        "inherit",
        [
            param(True, id="inherited_true"),
            param(False, id="inherited_false"),
        ],
    )
    async def test_field_validator_can_change_value(self, inherit: bool):
        class UserSchemaWithValidator(BaseModel):
            name: str

            @validator("name", allow_reuse=True)
            def fix_title(cls, v):
                return v.title()

            class Config:
                orm_mode = True

        attrs = {"name": "john doe"}
        create_user_body = {"data": {"attributes": attrs}}

        if inherit:
            UserSchemaWithValidator = self.inherit(UserSchemaWithValidator)
        app = self.build_app(UserSchemaWithValidator)

        async with AsyncClient(app=app, base_url="http://test") as client:
            url = app.url_path_for(f"get_{self.resource_type}_list")
            res = await client.post(url, json=create_user_body)
            assert res.status_code == status.HTTP_201_CREATED, res.text

            res_json = res.json()
            assert res_json["data"]
            assert res_json["data"].pop("id")
            assert res_json == {
                "data": {
                    "attributes": {"name": "John Doe"},
                    "type": "validator",
                },
                "jsonapi": {"version": "1.0"},
                "meta": None,
            }

    @mark.parametrize(
        ("name", "expected_detail"),
        [
            param("check_pre_1", "Raised 1 pre validator", id="check_1_pre_validator"),
            param("check_pre_2", "Raised 2 pre validator", id="check_2_pre_validator"),
            param("check_post_1", "Raised 1 post validator", id="check_1_post_validator"),
            param("check_post_2", "Raised 2 post validator", id="check_2_post_validator"),
        ],
    )
    async def test_root_validator(self, name: str, expected_detail: str):
        class UserSchemaWithValidator(BaseModel):
            name: str

            @root_validator(pre=True, allow_reuse=True)
            def validator_pre_1(cls, values):
                if values["name"] == "check_pre_1":
                    raise BadRequest(detail="Raised 1 pre validator")

                return values

            @root_validator(pre=True, allow_reuse=True)
            def validator_pre_2(cls, values):
                if values["name"] == "check_pre_2":
                    raise BadRequest(detail="Raised 2 pre validator")

                return values

            @root_validator(allow_reuse=True)
            def validator_post_1(cls, values):
                if values["name"] == "check_post_1":
                    raise BadRequest(detail="Raised 1 post validator")

                return values

            @root_validator(allow_reuse=True)
            def validator_post_2(cls, values):
                if values["name"] == "check_post_2":
                    raise BadRequest(detail="Raised 2 post validator")

                return values

            class Config:
                orm_mode = True

        attrs = {"name": name}
        create_user_body = {"data": {"attributes": attrs}}

        await self.execute_request_twice_and_check_response(
            schema=UserSchemaWithValidator,
            body=create_user_body,
            expected_detail=expected_detail,
        )

    @mark.parametrize(
        "inherit",
        [
            param(True, id="inherited_true"),
            param(False, id="inherited_false"),
        ],
    )
    async def test_root_validator_can_change_value(self, inherit: bool):
        class UserSchemaWithValidator(BaseModel):
            name: str

            @root_validator(allow_reuse=True)
            def fix_title(cls, v):
                v["name"] = v["name"].title()
                return v

            class Config:
                orm_mode = True

        attrs = {"name": "john doe"}
        create_user_body = {"data": {"attributes": attrs}}

        if inherit:
            UserSchemaWithValidator = self.inherit(UserSchemaWithValidator)
        app = self.build_app(UserSchemaWithValidator)

        async with AsyncClient(app=app, base_url="http://test") as client:
            url = app.url_path_for(f"get_{self.resource_type}_list")
            res = await client.post(url, json=create_user_body)
            assert res.status_code == status.HTTP_201_CREATED, res.text

            res_json = res.json()
            assert res_json["data"]
            assert res_json["data"].pop("id")
            assert res_json == {
                "data": {
                    "attributes": {"name": "John Doe"},
                    "type": "validator",
                },
                "jsonapi": {"version": "1.0"},
                "meta": None,
            }

    @mark.parametrize(
        ("name", "expected_detail"),
        [
            param("check_pre_1", "check_pre_1", id="check_1_pre_validator"),
            param("check_pre_2", "check_pre_2", id="check_2_pre_validator"),
            param("check_post_1", "check_post_1", id="check_1_post_validator"),
            param("check_post_2", "check_post_2", id="check_2_post_validator"),
        ],
    )
    async def test_root_validator_inheritance(self, name: str, expected_detail: str):
        class UserSchemaWithValidatorBase(BaseModel):
            name: str

            @root_validator(pre=True, allow_reuse=True)
            def validator_pre_1(cls, values):
                if values["name"] == "check_pre_1":
                    raise BadRequest(detail="Base check_pre_1")

                return values

            @root_validator(pre=True, allow_reuse=True)
            def validator_pre_2(cls, values):
                if values["name"] == "check_pre_2":
                    raise BadRequest(detail="Base check_pre_2")

                return values

            @root_validator(allow_reuse=True)
            def validator_post_1(cls, values):
                if values["name"] == "check_post_1":
                    raise BadRequest(detail="Base check_post_1")

                return values

            @root_validator(allow_reuse=True)
            def validator_post_2(cls, values):
                if values["name"] == "check_post_2":
                    raise BadRequest(detail="Base check_post_2")

                return values

            class Config:
                orm_mode = True

        class UserSchemaWithValidator(UserSchemaWithValidatorBase):
            name: str

            @root_validator(pre=True, allow_reuse=True)
            def validator_pre_1(cls, values):
                if values["name"] == "check_pre_1":
                    raise BadRequest(detail="check_pre_1")

                return values

            @root_validator(pre=True, allow_reuse=True)
            def validator_pre_2(cls, values):
                if values["name"] == "check_pre_2":
                    raise BadRequest(detail="check_pre_2")

                return values

            @root_validator(allow_reuse=True)
            def validator_post_1(cls, values):
                if values["name"] == "check_post_1":
                    raise BadRequest(detail="check_post_1")

                return values

            @root_validator(allow_reuse=True)
            def validator_post_2(cls, values):
                if values["name"] == "check_post_2":
                    raise BadRequest(detail="check_post_2")

                return values

            class Config:
                orm_mode = True

        attrs = {"name": name}
        create_user_body = {"data": {"attributes": attrs}}

        await self.execute_request_and_check_response(
            app=self.build_app(UserSchemaWithValidator),
            body=create_user_body,
            expected_detail=expected_detail,
        )


# todo: test errors
