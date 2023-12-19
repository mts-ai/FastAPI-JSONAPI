from copy import deepcopy
from typing import (
    Callable,
    Dict,
    Optional,
    Set,
    Type,
)

from pydantic import (
    class_validators,
    root_validator,
    validator,
)
from pydantic.fields import Validator
from pydantic.utils import unique_list

from fastapi_jsonapi.schema_base import BaseModel


def extract_root_validators(model: Type[BaseModel]) -> Dict[str, Callable]:
    pre_rv_new, post_rv_new = class_validators.extract_root_validators(model.__dict__)
    pre_root_validators = unique_list(
        model.__pre_root_validators__ + pre_rv_new,
        name_factory=lambda v: v.__name__,
    )
    post_root_validators = unique_list(
        model.__post_root_validators__ + post_rv_new,
        name_factory=lambda skip_on_failure_and_v: skip_on_failure_and_v[1].__name__,
    )

    result_validators = {}

    for validator_func in pre_root_validators:
        result_validators[validator_func.__name__] = root_validator(
            pre=True,
            allow_reuse=True,
        )(validator_func)

    for skip_on_failure, validator_func in post_root_validators:
        result_validators[validator_func.__name__] = root_validator(
            allow_reuse=True,
            skip_on_failure=skip_on_failure,
        )(validator_func)

    return result_validators


def _deduplicate_field_validators(validators: Dict) -> Dict:
    result_validators = {}

    for field_name, field_validators in validators.items():
        result_validators[field_name] = list(
            {
                # override in definition order
                field_validator.func.__name__: field_validator
                for field_validator in field_validators
            }.values(),
        )

    return result_validators


def extract_field_validators(
    model: Type[BaseModel],
    *,
    include_for_field_names: Optional[Set[str]] = None,
    exclude_for_field_names: Optional[Set[str]] = None,
):
    validators = class_validators.inherit_validators(
        class_validators.extract_validators(model.__dict__),
        deepcopy(model.__validators__),
    )
    validators = _deduplicate_field_validators(validators)
    validator_origin_param_keys = (
        "pre",
        "each_item",
        "always",
        "check_fields",
    )

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

        field_validator: Validator
        for field_validator in field_validators:
            validator_name = f"{field_name}_{field_validator.func.__name__}_validator"
            validator_params = {
                # copy validator params
                param_key: getattr(field_validator, param_key)
                for param_key in validator_origin_param_keys
            }
            result_validators[validator_name] = validator(
                field_name,
                **validator_params,
                allow_reuse=True,
            )(field_validator.func)

    return result_validators


def extract_validators(
    model: Type[BaseModel],
    exclude_for_field_names: Optional[Set[str]] = None,
) -> Dict[str, Callable]:
    return {
        **extract_field_validators(
            model,
            exclude_for_field_names=exclude_for_field_names,
        ),
        **extract_root_validators(model),
    }
