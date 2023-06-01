from typing import Dict, List

from tortoise.queryset import QuerySet


class SortTortoiseORM:
    @classmethod
    def sort(
        cls,
        query: QuerySet,
        query_params_sorting: List[Dict[str, str]],
        default_sort: str = "",
    ) -> QuerySet:
        """
        Реализация динамической сортировки для query.

        :param query: запрос
        :param query_params_sorting: параметры от клиента
        :param default_sort: дефолтная сортировка, например "-id" или `sort=-id,created_at`
        """
        if query_params_sorting:
            for i_sort in query_params_sorting:
                i_order = "" if i_sort["order"] == "asc" else "-"
                i_field = "{order}{field}".format(order=i_order, field=i_sort["field"])
                query = query.order_by(i_field)
        elif default_sort:
            query = query.order_by(default_sort)
        return query
