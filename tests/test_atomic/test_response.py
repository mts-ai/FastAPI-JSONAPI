import pytest

from fastapi_jsonapi.atomic.schemas import AtomicResultResponse


class TestAtomicResultResponse:
    @pytest.mark.parametrize(
        "operation_response",
        [
            {
                "atomic:results": [
                    {
                        "data": {
                            "links": {
                                "self": "https://example.com/blogPosts/13",
                            },
                            "type": "articles",
                            "id": "13",
                            "attributes": {
                                "title": "JSON API paints my bikeshed!",
                            },
                        },
                    },
                ],
            },
            {
                "atomic:results": [
                    {
                        "data": {
                            "links": {
                                "self": "https://example.com/authors/acb2ebd6-ed30-4877-80ce-52a14d77d470",
                            },
                            "type": "authors",
                            "id": "acb2ebd6-ed30-4877-80ce-52a14d77d470",
                            "attributes": {"name": "dgeb"},
                        },
                    },
                    {
                        "data": {
                            "links": {
                                "self": "https://example.com/articles/bb3ad581-806f-4237-b748-f2ea0261845c",
                            },
                            "type": "articles",
                            "id": "bb3ad581-806f-4237-b748-f2ea0261845c",
                            "attributes": {
                                "title": "JSON API paints my bikeshed!",
                            },
                            "relationships": {
                                "author": {
                                    "links": {
                                        "self": "https://example.com/articles/bb3ad581-806f-4237-b748-f2ea0261845c/relationships/author",
                                        "related": "https://example.com/articles/bb3ad581-806f-4237-b748-f2ea0261845c/author",
                                    },
                                },
                            },
                        },
                    },
                ],
            },
        ],
    )
    def test_response_data(self, operation_response: dict):
        validated = AtomicResultResponse.parse_obj(operation_response)
        assert validated.dict(exclude_unset=True, by_alias=True) == operation_response
