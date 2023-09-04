from __future__ import annotations

import pytest

from fastapi_jsonapi.atomic.schemas import AtomicOperationAction


@pytest.fixture()
def allowed_atomic_actions_list() -> list[str]:
    return [op.value for op in AtomicOperationAction]


@pytest.fixture()
def allowed_atomic_actions_as_string(allowed_atomic_actions_list) -> str:
    return ", ".join(repr(op) for op in allowed_atomic_actions_list)
