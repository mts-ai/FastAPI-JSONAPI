from itertools import chain
from json import dumps
from typing import Dict, List

from fastapi import FastAPI, status
from httpx import AsyncClient
from pytest import mark, param  # noqa PT013

from fastapi_jsonapi.views.view_base import ViewBase
from tests.fixtures.entities import create_user
from tests.misc.utils import fake
from tests.models import (
    Computer,
    Post,
    PostComment,
    User,
    UserBio,
)
from tests.schemas import (
    UserBaseSchema,
    UserBioBaseSchema,
)

pytestmark = mark.asyncio


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


async def test_get_list_view_generic(client: AsyncClient, user_1: User):
    res = await client.get("/users")
    assert res
    assert res.status_code == status.HTTP_200_OK
    response_json = res.json()
    users_data = response_json["data"]
    assert len(users_data) == 1, users_data
    user_data = users_data[0]
    assert user_data["id"] == str(user_1.id)
    assert user_data["attributes"] == UserBaseSchema.from_orm(user_1)


async def test_get_user_not_found(client: AsyncClient):
    fake_id = fake.pyint()
    res = await client.get(f"/users/{fake_id}")

    assert res.json() == {
        "errors": [
            {
                "detail": f"Resource User `{fake_id}` not found",
                "title": "Resource not found.",
                "status_code": 404,
                "meta": {"parameter": "id"},
            },
        ],
    }


class TestCreateObjects:
    async def test_create_object(self, client: AsyncClient):
        create_user_body = {
            "data": {
                "attributes": {
                    "name": fake.name(),
                    "age": fake.pyint(),
                    "email": fake.email(),
                },
            },
        }
        res = await client.post("/users", json=create_user_body)
        assert res.status_code == status.HTTP_201_CREATED, res.text
        response_data = res.json()
        assert "data" in response_data, response_data
        assert response_data["data"]["attributes"] == create_user_body["data"]["attributes"]

    async def test_create_object_with_relationship_and_fetch_include(self, client: AsyncClient, user_1: User):
        create_user_bio_body = {
            "data": {
                "attributes": UserBioBaseSchema(
                    birth_city=fake.word(),
                    favourite_movies=fake.sentence(),
                    keys_to_ids_list={"foobar": [1, 2, 3], "spameggs": [2, 3, 4]},
                ).dict(),
                "relationships": {"user": {"data": {"type": "user", "id": user_1.id}}},
            },
        }
        res = await client.post("/user-bio?include=user", json=create_user_bio_body)
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
        assert included_user["attributes"] == UserBaseSchema.from_orm(user_1)

    async def test_create_object_with_to_many_relationship_and_fetch_include(
        self,
        client: AsyncClient,
        computer_1: Computer,
        computer_2: Computer,
    ):
        create_user_body = {
            "data": {
                "attributes": {
                    "name": fake.name(),
                    "age": fake.pyint(),
                    "email": fake.email(),
                },
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
        res = await client.post("/users?include=computers", json=create_user_body)
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
                    "relationships": None,
                    "type": "computer",
                },
                {
                    "attributes": {"name": computer_2.name},
                    "id": str(computer_2.id),
                    "relationships": None,
                    "type": "computer",
                },
            ],
            "jsonapi": {"version": "1.0"},
            "meta": None,
        }

    async def test_create_user(self, client: AsyncClient):
        create_user_body = {
            "data": {
                "attributes": {
                    "name": fake.name(),
                    "age": fake.pyint(),
                    "email": fake.email(),
                },
            },
        }
        res = await client.post("/users", json=create_user_body)
        assert res.status_code == status.HTTP_201_CREATED, res.text
        response_data: dict = res.json()
        assert "data" in response_data, response_data
        assert response_data["data"]["attributes"] == create_user_body["data"]["attributes"]

    async def test_create_user_and_fetch_data(self, client: AsyncClient):
        create_user_body = {
            "data": {
                "attributes": {
                    "name": fake.name(),
                    "age": fake.pyint(),
                    "email": fake.email(),
                },
            },
        }
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


class TestPatchObjects:
    async def test_patch_object(self, client: AsyncClient, user_1: User):
        new_attrs = UserBaseSchema(
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
        # TODO: add related fixtures and check includes
        res = await client.patch(f"/users/{user_1.id}?include=computers", json=patch_user_body)
        assert res.status_code == status.HTTP_200_OK, res.text

        assert res.json() == {
            "data": {
                "attributes": new_attrs,
                "id": str(user_1.id),
                "relationships": {"computers": {"data": []}},
                "type": "user",
            },
            "included": [],
            "jsonapi": {"version": "1.0"},
            "meta": None,
        }


class TestDeleteObjects:
    async def test_delete_object_and_fetch_404(self, client: AsyncClient, user_1: User):
        res = await client.delete(f"/users/{user_1.id}")
        assert res.status_code == status.HTTP_200_OK, res.text
        assert res.json() == {
            "data": {
                "attributes": UserBaseSchema.from_orm(user_1),
                "id": str(user_1.id),
                "type": "user",
            },
            "jsonapi": {"version": "1.0"},
            "meta": None,
        }

        res = await client.get(f"/users/{user_1.id}")
        assert res.status_code == status.HTTP_404_NOT_FOUND, res.text

        res = await client.get("/users")
        assert res.status_code == status.HTTP_200_OK, res.text
        assert res.json() == {
            "data": [],
            "jsonapi": {"version": "1.0"},
            "meta": {"count": 0, "totalPages": 1},
        }

    async def test_delete_objects_many(
        self,
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

        res = await client.delete("/users", params=params)
        assert res.status_code == status.HTTP_200_OK, res.text
        assert res.json() == {
            "data": [
                {
                    "attributes": UserBaseSchema.from_orm(user_1),
                    "id": str(user_1.id),
                    "type": "user",
                },
                {
                    "attributes": UserBaseSchema.from_orm(user_3),
                    "id": str(user_3.id),
                    "type": "user",
                },
            ],
            "jsonapi": {"version": "1.0"},
            "meta": {"count": 2, "totalPages": 1},
        }

        res = await client.get("/users")
        assert res.status_code == status.HTTP_200_OK, res.text
        assert res.json() == {
            "data": [
                {
                    "attributes": UserBaseSchema.from_orm(user_2),
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


class TestFilters:
    async def test_filters_really_works(
        self,
        client: AsyncClient,
        user_1: User,
        user_2: User,
    ):
        params = {"filter[name]": fake.name()}
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
        client: AsyncClient,
        user_1: User,
        user_2: User,
        field_name: str,
    ):
        params = {f"filter[{field_name}]": getattr(user_1, field_name)}
        res = await client.get("/users", params=params)
        assert res.status_code == status.HTTP_200_OK, res.text
        assert res.json() == {
            "data": [
                {
                    "attributes": UserBaseSchema.from_orm(user_1).dict(),
                    "id": str(user_1.id),
                    "type": "user",
                },
            ],
            "jsonapi": {"version": "1.0"},
            "meta": {"count": 1, "totalPages": 1},
        }

    async def test_several_field_filters_at_the_same_time(
        self,
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
        res = await client.get("/users", params=params)
        assert res.status_code == status.HTTP_200_OK, res.text
        assert res.json() == {
            "data": [
                {
                    "attributes": UserBaseSchema.from_orm(user_1).dict(),
                    "id": str(user_1.id),
                    "type": "user",
                },
            ],
            "jsonapi": {"version": "1.0"},
            "meta": {"count": 1, "totalPages": 1},
        }

    async def test_field_filters_with_values_from_different_models(
        self,
        client: AsyncClient,
        user_1: User,
        user_2: User,
    ):
        params_user_1 = {"filter[name]": user_1.name}

        assert user_1.age != user_2.age
        params_user_2 = {"filter[age]": user_2.age}

        res = await client.get("/users", params=params_user_2 | params_user_1)
        assert res.status_code == status.HTTP_200_OK, res.text
        assert res.json() == {
            "data": [],
            "jsonapi": {"version": "1.0"},
            "meta": {"count": 0, "totalPages": 1},
        }

    async def test_composite_filter_by_one_field(
        self,
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

        res = await client.get("/users", params=params)
        assert res.status_code == status.HTTP_200_OK, res.text
        assert res.json() == {
            "data": [
                {
                    "attributes": UserBaseSchema.from_orm(user_1),
                    "id": str(user_1.id),
                    "type": "user",
                },
                {
                    "attributes": UserBaseSchema.from_orm(user_3),
                    "id": str(user_3.id),
                    "type": "user",
                },
            ],
            "jsonapi": {"version": "1.0"},
            "meta": {"count": 2, "totalPages": 1},
        }

    async def test_composite_filter_by_several_fields(
        self,
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

        res = await client.get("/users", params=params)
        assert res.status_code == status.HTTP_200_OK, res.text
        assert res.json() == {
            "data": [
                {
                    "attributes": UserBaseSchema.from_orm(user_1),
                    "id": str(user_1.id),
                    "type": "user",
                },
            ],
            "jsonapi": {"version": "1.0"},
            "meta": {"count": 1, "totalPages": 1},
        }

    async def test_composite_filter_with_mutually_exclusive_conditions(
        self,
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

        res = await client.get("/users", params=params)
        assert res.status_code == status.HTTP_200_OK, res.text
        assert res.json() == {
            "data": [],
            "jsonapi": {"version": "1.0"},
            "meta": {"count": 0, "totalPages": 1},
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
    async def test_sort(self, client: AsyncClient, async_session, order: str):
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
        res = await client.get("/users", params=params)
        assert res.status_code == status.HTTP_200_OK, res.text
        assert res.json() == {
            "data": sorted(
                [
                    {
                        "attributes": UserBaseSchema.from_orm(user_1).dict(),
                        "id": str(user_1.id),
                        "type": "user",
                    },
                    {
                        "attributes": UserBaseSchema.from_orm(user_3).dict(),
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


# todo: test object not found
