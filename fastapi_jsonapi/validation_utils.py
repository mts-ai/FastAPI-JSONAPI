from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import field_validator, model_validator

if TYPE_CHECKING:
    from pydantic import BaseModel as PydanticBaseModel
    from pydantic._internal._decorators import DecoratorInfos
    from pydantic.functional_validators import _V2Validator


# TODO: handle model validators? (info.model_validator)
def extract_validators(
    model: type[PydanticBaseModel],
    include_for_field_names: set[str] | None = None,
    exclude_for_field_names: set[str] | None = None,
) -> dict[str, _V2Validator]:
    validators: DecoratorInfos = model.__pydantic_decorators__

    exclude_for_field_names = exclude_for_field_names or set()
    if include_for_field_names and exclude_for_field_names:
        include_for_field_names = include_for_field_names.difference(
            exclude_for_field_names,
        )

    result_validators = {}

    # field validators
    for name, validator in validators.field_validators.items():
        for field_name in validator.info.fields:
            # exclude
            if field_name in exclude_for_field_names:
                continue

            # or include
            if include_for_field_names and field_name not in include_for_field_names:
                continue

            validator_config = field_validator(field_name, mode=validator.info.mode)
            result_validators[name] = validator_config(validator.func)

    # model validators
    for name, validator in validators.model_validators.items():
        validator_config = model_validator(mode=validator.info.mode)
        result_validators[name] = validator_config(validator.func)

    return result_validators
