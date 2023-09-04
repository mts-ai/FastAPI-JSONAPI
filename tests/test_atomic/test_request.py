import pytest
from pydantic import ValidationError

from fastapi_jsonapi.atomic.schemas import AtomicOperationRequest
from tests.misc.utils import fake


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

    def test_not_supported_operation(
        self,
        allowed_atomic_actions_as_string: str,
    ):
        operation_name = fake.word()
        atomic_request_data = {
            "atomic:operations": [
                {
                    "op": operation_name,
                    "href": "/any",
                    "data": {
                        "type": "any",
                        "attributes": {
                            "any": "any",
                        },
                    },
                },
            ],
        }
        with pytest.raises(ValidationError) as exc_info:
            AtomicOperationRequest.parse_obj(atomic_request_data)
        errors = exc_info.value.errors()
        error = errors[0]
        assert (
            error.get("msg")
            == f"value is not a valid enumeration member; permitted: {allowed_atomic_actions_as_string}"
        )
