from __future__ import annotations

from typing import Sequence

import pytest

from fastapi_jsonapi.atomic.schemas import AtomicOperationAction


@pytest.fixture()
def allowed_atomic_actions_list() -> list[str]:
    return [op.value for op in AtomicOperationAction]


def options_as_pydantic_choices_string(options: Sequence[str]) -> str:
    if len(options) == 1:
        return repr(options[0])
    return " or ".join(
        (
            ", ".join(repr(op) for op in options[:-1]),
            repr(options[-1]),
        ),
    )


@pytest.fixture()
def atomic_operation_actions_as_str():
    return options_as_pydantic_choices_string([v.value for v in AtomicOperationAction])


@pytest.fixture()
def allowed_atomic_actions_as_string(allowed_atomic_actions_list) -> str:
    return options_as_pydantic_choices_string(allowed_atomic_actions_list)
