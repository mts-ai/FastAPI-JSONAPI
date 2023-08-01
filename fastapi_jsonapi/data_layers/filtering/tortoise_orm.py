"""Tortoise filters creator."""

from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    Union,
)

from pydantic import BaseModel
from pydantic.fields import ModelField
from tortoise.expressions import Q
from tortoise.queryset import QuerySet

from fastapi_jsonapi.data_layers.fields.enum import Enum
from fastapi_jsonapi.data_layers.filtering.tortoise_operation import prepare_field_name_for_filtering
from fastapi_jsonapi.data_layers.orm import DBORMOperandType
from fastapi_jsonapi.data_typing import TypeModel
from fastapi_jsonapi.exceptions import InvalidFilters, QueryError
from fastapi_jsonapi.jsonapi_typing import Filters
from fastapi_jsonapi.querystring import QueryStringManager


def prepare_filter_pair(field: Type[ModelField], field_name: str, type_op: str, value: Any) -> Tuple:
    """Prepare filter."""
    name_field_q: str = prepare_field_name_for_filtering(field_name, type_op)
    return name_field_q, value


class FilterTortoiseORM:
    def __init__(self, model: TypeModel):
        self.model = model

    def create_query(self, filter_q: Union[tuple, Q]) -> Q:
        """Tortoise filter creation."""
        if isinstance(filter_q, tuple):
            return Q(**{filter_q[0]: filter_q[1]})
        else:
            return Q(filter_q)

    def orm_and_or(
        self,
        op: DBORMOperandType,
        filters: list,
    ) -> Union[None, QuerySet, Dict[str, Union[QuerySet, List[QuerySet]]]]:
        """Filter for query to ORM."""
        if not filters:
            return None
        if op is DBORMOperandType.or_:
            result_filter = None
            for i_filter in filters:
                i_filter = i_filter[0] if isinstance(i_filter, list) else i_filter  # noqa: PLW2901
                if result_filter is None:
                    result_filter = self.create_query(i_filter)
                else:
                    result_filter |= self.create_query(i_filter)
            return result_filter
        if op is DBORMOperandType.and_:
            result_filter = None
            for i_filter in filters:
                i_filter = i_filter[0] if isinstance(i_filter, list) else i_filter  # noqa: PLW2901
                if result_filter is None:
                    result_filter = self.create_query(i_filter)
                else:
                    result_filter &= self.create_query(i_filter)
            return result_filter
        if op is DBORMOperandType.not_:
            return ~Q(**{filters[0][0][0]: filters[0][0][1]})
        return None

    def filter_converter(
        self,
        schema: Type[BaseModel],
        filters: Filters,
    ) -> List:
        """
        Make a list with filters, which can be used in the tortoise filter.

        :param schema: schemas schema of object.
        :param filters: list of JSON API filters.
        :return: list of filters, prepared for use in tortoise model.
        :raises InvalidFilters: if the filter was created with an error.
        """
        converted_filters: List = []
        for i_filter in filters:
            if "or" in i_filter:
                result = self.filter_converter(schema, i_filter["or"])
                converted_filters.append(self.orm_and_or(DBORMOperandType.or_, result))
                continue
            elif "and" in i_filter:
                result = self.filter_converter(schema, i_filter["and"])
                converted_filters.append(self.orm_and_or(DBORMOperandType.and_, result))
                continue
            elif "not" in i_filter:
                result = self.filter_converter(schema, [i_filter["not"]])
                converted_filters.append(self.orm_and_or(DBORMOperandType.not_, result))
                continue
            model_fields = i_filter["name"].split(".")
            name_field: str = model_fields[0]
            if len(model_fields) > 1:
                result = self.filter_converter(
                    schema.__fields__[name_field].type_,
                    [
                        {
                            "name": ".".join(model_fields[1:]),
                            "op": i_filter["op"],
                            "val": i_filter["val"],
                        },
                    ],
                )
                converted_filters.append(result)
            else:
                val: Union[List[Any], Any]
                field: ModelField = schema.__fields__[name_field]
                if isinstance(i_filter["val"], list) and field.type_ is not list:
                    val = self._validate(i_filter, field)
                else:
                    val, errors = field.validate(i_filter["val"], {}, loc=field.alias)
                    val = self.val_to_query(val)
                    if errors:
                        raise InvalidFilters(str(errors), parameter=field.alias)

                converted_filters.append(prepare_filter_pair(field, name_field, i_filter["op"], val))
        return converted_filters

    async def json_api_filter(
        self,
        query,
        schema: Type[BaseModel],
        query_params: QueryStringManager,
    ) -> QuerySet:
        """Make queries with filtering from request."""
        filters = self.filter_converter(
            schema=schema,
            filters=query_params.filters,
        )
        for i_filter in filters:
            query = query.filter(**{i_filter[0]: i_filter[1]})
        return query

    def val_to_query(self, val: Any) -> Any:
        """Value to query."""
        if isinstance(val, Enum):
            val = val.value
        return val

    def _validate(self, json_api_filter: Dict[str, List[str]], model_filed: ModelField) -> List:
        val = []
        for i_v in json_api_filter["val"]:
            i_val, errors = model_filed.validate(i_v, {}, loc=model_filed.alias)
            if errors:
                raise InvalidFilters(str(errors), parameter=model_filed.alias)
            i_val = self.val_to_query(i_val)
            val.append(i_val)
        return val

    def validate(self, filter_q: Union[None, Q, Dict[str, Union[Q, List[Q]]]]) -> Optional[Q]:
        """
        Tortoise filter validation.

        :param filter_q: dict with filter body.
        :return: validated filter.
        :raises QueryError: if the field in the filter does not match the field in tortoise.
        """
        if isinstance(filter_q, Q):
            return Q(filter_q)
        elif filter_q is None:
            return None
        else:
            msg = "An unexpected argument for Q (result_filter={type})".format(type=type(filter_q))
            raise QueryError(msg)
