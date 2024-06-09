from typing import (
    TypeVar,
    Type,
    Generator,
    TYPE_CHECKING,
)


if TYPE_CHECKING:
    # noinspection PyProtectedMember
    from pydantic.fields import FieldInfo

SearchType = TypeVar("SearchType")


class MetadataInstanceSearch:
    def __init__(self, search_type: Type[SearchType]):
        self.search_type = search_type

    def iterate(self, field: "FieldInfo") -> Generator[SearchType, None, None]:
        for elem in field.metadata:
            if isinstance(elem, self.search_type):
                yield elem

        return None

    def first(self, field: "FieldInfo") -> SearchType | None:
        return next(self.iterate(field), None)