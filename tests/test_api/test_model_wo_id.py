"""
Tests for custom id name.

Check cases when model is w/o `id` field
"""

from fastapi import FastAPI
from httpx import AsyncClient
from starlette import status

from examples.api_for_sqlalchemy.models import AgeRating
from examples.api_for_sqlalchemy.schemas import AgeRatingAttributesSchema, MovieAttributesSchema
from tests.misc.utils import fake


async def test_get_age_rating_list(
    app: FastAPI,
    client: AsyncClient,
    age_rating_g: AgeRating,
):
    """
    Get age rating list, no `id` field on model
    """
    url = app.url_path_for("get_age-rating_list")
    response = await client.get(url)
    assert response.status_code == status.HTTP_200_OK, response.text
    response_data = response.json()
    assert "data" in response_data, response_data
    expected_data = {
        "data": [
            {
                "id": age_rating_g.name,
                "attributes": AgeRatingAttributesSchema.model_validate(age_rating_g).model_dump(),
                "type": "age-rating",
            },
        ],
        "meta": {
            # we expect that db was empty before the test.
            # the only age rating obj was created in a fixture.
            "count": 1,
            "totalPages": 1,
        },
        "jsonapi": {"version": "1.0"},
    }
    assert response_data == expected_data


async def test_create_with_related_age_rating(
    app: FastAPI,
    client: AsyncClient,
    age_rating_g: AgeRating,
):
    """
    Create with related age rating, no `id` field on model.

    Field `name` is used for `id`.
    Check relation is created, new related object is included.
    """
    url = app.url_path_for("get_movie_list")
    url = f"{url}?include=age_rating_obj"

    movie_attributes_obj = MovieAttributesSchema(
        title=fake.name(),
        description=fake.sentence(),
    )
    movie_attributes = movie_attributes_obj.model_dump(exclude_unset=True)
    assert "age_rating" not in movie_attributes, "don't provide this field, it should be a related obj"
    relationship_data = {
        "age_rating_obj": {
            "data": {
                "type": "age-rating",
                "id": age_rating_g.name,
            },
        },
    }
    movie_create = {
        "data": {
            "attributes": movie_attributes,
            "relationships": relationship_data,
        },
    }
    response = await client.post(url, json=movie_create)
    assert response.status_code == status.HTTP_201_CREATED, response.text
    response_data = response.json()
    movie_data: dict = response_data["data"]
    assert movie_data.pop("id")
    movie_attributes_obj.age_rating = age_rating_g.name
    assert movie_data == {
        "type": "movie",
        "attributes": movie_attributes_obj.model_dump(),
        "relationships": relationship_data,
    }

    included = response_data["included"]
    assert included == [
        {
            "id": age_rating_g.name,
            "type": "age-rating",
            "attributes": AgeRatingAttributesSchema.model_validate(age_rating_g).model_dump(exclude_unset=True),
        },
    ]
