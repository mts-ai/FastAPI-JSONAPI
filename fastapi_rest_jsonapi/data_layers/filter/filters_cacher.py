"""Filter caches module."""

from copy import deepcopy
from functools import reduce
from typing import (
    Callable,
    Dict,
    List,
    Optional,
    Union,
)


class FiltersCacher:
    """Filter cacher."""

    def __init__(
        self, conditions: List[Dict[str, Union[int, float, str, bool]]], getter_callback: Optional[Callable] = None
    ):
        """Init getter callback and cached condition."""
        self._getter_callback: Callable = getter_callback if getter_callback else lambda values, key: values[key]
        self._cached_condition: Callable = self._cache_condition_depth_first(conditions)

    def compare(self, values_dict: Dict[str, Union[int, float, str, bool]]) -> bool:
        """Apply conditions to values."""
        return self._cached_condition(values_dict)

    def _cache_condition_depth_first(self, conditions: List[Dict[str, Union[int, float, str, bool]]]) -> Callable:
        """
        Cache condition depth.

        :param conditions: list of conditions.
        :return: condition.
        """
        temp_list = list()
        for i_condition in conditions:
            if i_condition.get("and"):
                temp_list.append(self._cache_condition_depth_first(i_condition["and"]))
                closure = self._and(temp_list)
                temp_list.clear()
            elif i_condition.get("or"):
                and_closure = self._and(temp_list)
                closure = self._or([and_closure, self._cache_condition_depth_first(i_condition["or"])])
                temp_list.clear()
            elif i_condition.get("not"):
                inverted = i_condition.get("not")
                operator = "_{op}".format(op=inverted["op"])
                temp_closure = getattr(self, operator)(name=inverted["name"], val=inverted["val"])
                closure = self._not(temp_closure)
            else:
                operator = "_{op}".format(op=i_condition["op"])
                closure = getattr(self, operator)(name=i_condition["name"], val=i_condition["val"])
            temp_list.append(closure)
        if len(temp_list) > 1:
            result = self._and(temp_list)
        else:
            result = temp_list.pop()
        return result

    def _eq(self, name: str, val: Union[str, int, float, bool]) -> Callable:
        """Equal closure."""
        eq_callback: Callable = self._getter_callback

        def equals(values_dict: Dict[str, Union[str, int, float, bool]]) -> bool:
            compare_value = eq_callback(values_dict, name)
            return compare_value == val

        return equals

    def _ne(self, name: str, val: Union[str, int, float, bool]) -> Callable:
        """Not equal closure."""
        ne_callback: Callable = self._getter_callback

        def not_equals(values_dict: Dict[str, Union[str, int, float, bool]]) -> bool:
            compare_value = ne_callback(values_dict, name)
            return compare_value != val

        return not_equals

    def _gt(self, name: str, val: Union[str, int, float, bool]) -> Callable:
        """Grater than closure."""
        gt_callback: Callable = self._getter_callback

        def greater(values_dict: Dict[str, Union[str, int, float, bool]]) -> bool:
            compare_value = gt_callback(values_dict, name)
            return compare_value > val

        return greater

    def _ge(self, name: str, val: Union[str, int, float, bool]) -> Callable:
        """Grater or equal closure."""
        ge_callback: Callable = self._getter_callback

        def greater_or_equal(values_dict: Dict[str, Union[str, int, float, bool]]) -> bool:
            compare_value = ge_callback(values_dict, name)
            return compare_value >= val

        return greater_or_equal

    def _lt(self, name: str, val: Union[str, int, float, bool]) -> Callable:
        """Less than closure."""
        lt_callback: Callable = self._getter_callback

        def less(values_dict: Dict[str, Union[str, int, float, bool]]) -> bool:
            compare_value = lt_callback(values_dict, name)
            return compare_value < val

        return less

    def _le(self, name: str, val: Union[str, int, float, bool]) -> Callable:
        """Less than closure."""
        le_callback: Callable = self._getter_callback

        def less_or_equal(values_dict: Dict[str, Union[str, int, float, bool]]) -> bool:
            compare_value = le_callback(values_dict, name)
            return compare_value <= val

        return less_or_equal

    def _startswith(self, name: str, val: Union[str, int, float, bool]) -> Callable:
        """Startwith closure."""
        startswith_callback: Callable = self._getter_callback

        def startswith(values_dict: Dict[str, Union[str, int, float, bool]]) -> bool:
            compare_value = startswith_callback(values_dict, name)
            return compare_value.startswith(val)

        return startswith

    def _endswith(self, name: str, val: Union[str, int, float, bool]) -> Callable:
        """Endwith closure."""
        endswith_callback: Callable = self._getter_callback

        def endswith(values_dict: Dict[str, Union[str, int, float, bool]]) -> bool:
            compare_value = endswith_callback(values_dict, name)
            return compare_value.endswith(val)

        return endswith

    def _like(self, name: str, val: Union[str, int, float, bool]) -> Callable:
        """Like expression closure."""
        like_callback: Callable = self._getter_callback

        def like(values_dict: Dict[str, Union[str, int, float, bool]]) -> bool:
            compare_value = like_callback(values_dict, name)
            return compare_value in val

        return like

    def _ilike(self, name: str, val: Union[str, int, float, bool]) -> Callable:
        """Ilike expression closure."""
        ilike_callback: Callable = self._getter_callback
        val = val.lower()

        def ilike(values_dict: Dict[str, Union[str, int, float, bool]]) -> bool:
            compare_value = ilike_callback(values_dict, name)
            return compare_value.lower() in val

        return ilike

    def _notlike(self, name: str, val: Union[str, int, float, bool]) -> Callable:
        """Not like expression closure."""
        notlike_callback: Callable = self._getter_callback

        def notlike(values_dict: Dict[str, Union[str, int, float, bool]]) -> bool:
            compare_value = notlike_callback(values_dict, name)
            return compare_value not in val

        return notlike

    def _notilike(self, name: str, val: Union[str, int, float, bool]) -> Callable:
        """Not ilike expression closure."""
        notilike_callback: Callable = self._getter_callback
        val = val.lower()

        def notilike(values_dict: Dict[str, Union[str, int, float, bool]]) -> bool:
            compare_value = notilike_callback(values_dict, name)
            return compare_value.lower() not in val

        return notilike

    def _in_(self, name: str, val: Union[str, int, float, bool]) -> Callable:  # noqa: WPS120
        """In closure."""
        in_callback: Callable = self._getter_callback
        val = set(val)

        def in_(values_dict: Dict[str, Union[str, int, float, bool]]) -> bool:
            compare_value = in_callback(values_dict, name)
            return compare_value in val

        return in_

    def _notin_(self, name: str, val: Union[str, int, float, bool]) -> Callable:  # noqa: WPS120
        """Not in closure."""
        notin_callback: Callable = self._getter_callback
        val = set(val)

        def notin(values_dict: Dict[str, Union[str, int, float, bool]]) -> bool:
            compare_value = notin_callback(values_dict, name)
            return compare_value not in val

        return notin

    @classmethod
    def _and(cls, condition_list: List[Callable]) -> Callable:
        """And closure."""
        cond_list: List[Callable] = deepcopy(condition_list)

        def and_(values_dict: Dict[str, Union[str, int, float, bool]]) -> bool:
            return reduce(lambda acc, i_closure: acc and i_closure(values_dict), cond_list, True)  # noqa: WPS425

        return and_

    @classmethod
    def _or(cls, condition_list: List[Callable]) -> Callable:
        """Or closure."""
        cond_list: List[Callable] = deepcopy(condition_list)

        def or_(values_dict: Dict[str, Union[str, int, float, bool]]) -> bool:
            return reduce(lambda acc, i_closure: acc or i_closure(values_dict), cond_list, False)  # noqa: WPS425

        return or_

    @classmethod
    def _not(cls, closure: Callable) -> Callable:
        """Not closure."""

        def inverted_closure(values_dict: Dict[str, Union[str, int, float, bool]]) -> bool:
            return not (closure(values_dict))

        return inverted_closure
