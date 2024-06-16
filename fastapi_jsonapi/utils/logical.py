from typing import Any


def logical_xor(left: Any, right: Any) -> bool:
    return bool(left) != bool(right)
