import json
from unittest.mock import MagicMock

import pytest
from fastapi import status
from starlette.datastructures import QueryParams

from fastapi_jsonapi.exceptions import InvalidFilters
from fastapi_jsonapi.exceptions.json_api import BadRequest
from fastapi_jsonapi.querystring import QueryStringManager


def test__extract_item_key():
    manager = QueryStringManager(MagicMock())

    key = "fields[user]"
    assert manager._extract_item_key(key) == "user"

    with pytest.raises(BadRequest) as exc_info:  # noqa: PT012
        key = "fields[user"
        manager._extract_item_key(key)

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc_info.value.detail == {
        "errors": [
            {
                "status_code": status.HTTP_400_BAD_REQUEST,
                "source": {"parameter": "fields[user"},
                "title": "Bad Request",
                "detail": "Parse error",
            },
        ],
    }


def test_querystring():
    request = MagicMock()
    request.query_params = QueryParams([("fields[user]", "name")])
    manager = QueryStringManager(request)
    assert manager.querystring == {"fields[user]": "name"}


def test_filters__errors():
    request = MagicMock()
    request.query_params = QueryParams([("filter", "not_json")])
    manager = QueryStringManager(request)

    with pytest.raises(InvalidFilters) as exc_info:
        manager.filters

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc_info.value.detail == {
        "errors": [
            {
                "status_code": status.HTTP_400_BAD_REQUEST,
                "source": {"parameter": "filters"},
                "title": "Invalid filters querystring parameter.",
                "detail": "Parse error",
            },
        ],
    }

    request.query_params = QueryParams(
        [
            (
                "filter",
                json.dumps(
                    {
                        "name": "",
                        "op": "",
                        "val": "",
                    },
                ),
            ),
        ],
    )
    manager = QueryStringManager(request)

    with pytest.raises(InvalidFilters) as exc_info:
        manager.filters

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc_info.value.detail == {
        "errors": [
            {
                "status_code": status.HTTP_400_BAD_REQUEST,
                "source": {"parameter": "filters"},
                "title": "Invalid filters querystring parameter.",
                "detail": "Incorrect filters format, expected list of conditions but got dict",
            },
        ],
    }
