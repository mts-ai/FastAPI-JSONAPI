from copy import deepcopy
from typing import TYPE_CHECKING, Callable, Dict, Optional, Set, Type

from pydantic import field_validator, model_validator

from fastapi_jsonapi.schema_base import BaseModel

if TYPE_CHECKING:
    from pydantic._internal._decorators import DecoratorInfos


def extract_root_validators(model: Type[BaseModel]) -> Dict[str, Callable]:
    pre_root_validators = getattr(model, "__pre_root_validators__", [])
    post_root_validators = getattr(model, "__post_root_validators__", [])
    result_validators = {}
    for validator_func in pre_root_validators:
        result_validators[validator_func.__name__] = model_validator(mode="before")

    for validator_func in post_root_validators:
        result_validators[validator_func.__name__] = model_validator(
            mode="before",
        )

    return result_validators


def _deduplicate_field_validators(validators: "DecoratorInfos") -> Dict:
    result_validators = {}
    field_validators = validators.field_validators
    model_validators = validators.model_validators

    for category_validators in [field_validators, model_validators]:
        for validator_name, field_validator_ in category_validators.items():
            func_name = field_validator_.func.__name__

            if func_name not in result_validators:
                result_validators[func_name] = field_validator_

    return result_validators


def extract_field_validators(
    model: Type[BaseModel],
    include_for_field_names: Optional[Set[str]] = None,
    exclude_for_field_names: Optional[Set[str]] = None,
):
    validators = _deduplicate_field_validators(deepcopy(model.__pydantic_decorators__))

    exclude_for_field_names = exclude_for_field_names or set()
    if include_for_field_names and exclude_for_field_names:
        include_for_field_names = include_for_field_names.difference(
            exclude_for_field_names,
        )

    result_validators = {}
    for field_name, field_validators in validators.items():
        if field_name in exclude_for_field_names:
            continue

        if include_for_field_names and field_name not in include_for_field_names:
            continue

        validator_name = f"{field_name}_{field_validator.__name__}_validator"
        result_validators[validator_name] = field_validator(
            field_name,
        )(field_validators.func)

    return result_validators


def extract_validators(
    model: Type[BaseModel],
    exclude_for_field_names: Optional[Set[str]] = None,
) -> Dict[str, Callable]:
    return {
        **extract_field_validators(
            model=model,
            exclude_for_field_names=exclude_for_field_names,
        ),
        **extract_root_validators(model),
    }
