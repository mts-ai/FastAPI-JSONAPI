import pytest

from fastapi_jsonapi.atomic.schemas import AtomicOperationRequest


class TestAtomicOperationRequest:
    @pytest.mark.parametrize(
        "operation_request",
        [
            {
                "atomic:operations": [
                    {
                        "op": "add",
                        "href": "/blogPosts",
                        "data": {
                            "type": "articles",
                            "attributes": {
                                "title": "JSON API paints my bikeshed!",
                            },
                        },
                    },
                ],
            },
            {
                "atomic:operations": [
                    {
                        "op": "update",
                        "data": {
                            "type": "articles",
                            "id": "13",
                            "attributes": {"title": "To TDD or Not"},
                        },
                    },
                ],
            },
            {
                "atomic:operations": [
                    {
                        "op": "remove",
                        "ref": {
                            "type": "articles",
                            "id": "13",
                        },
                    },
                ],
            },
            {
                # the following request assigns a to-one relationship:
                "atomic:operations": [
                    {
                        "op": "update",
                        "ref": {
                            "type": "articles",
                            "id": "13",
                            "relationship": "author",
                        },
                        "data": {
                            "type": "people",
                            "id": "9",
                        },
                    },
                ],
            },
            {
                # the following request clears a to-one relationship
                "atomic:operations": [
                    {
                        "op": "update",
                        "ref": {
                            "type": "articles",
                            "id": "13",
                            "relationship": "author",
                        },
                        "data": None,
                    },
                ],
            },
        ],
    )
    def test_request_data(self, operation_request: dict):
        validated = AtomicOperationRequest.parse_obj(operation_request)
        assert validated.dict(exclude_unset=True, by_alias=True) == operation_request
