from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi_jsonapi.types_metadata import (
    ClientCanSetId,
    CustomFilterSQL,
    RelationshipInfo,
)
from fastapi_jsonapi.utils.metadata_instance_search import MetadataInstanceSearch

if TYPE_CHECKING:
    # noinspection PyProtectedMember
    from pydantic.fields import FieldInfo

search_client_can_set_id = MetadataInstanceSearch[ClientCanSetId](ClientCanSetId)
search_relationship_info = MetadataInstanceSearch[RelationshipInfo](RelationshipInfo)
search_custom_filter_sql = MetadataInstanceSearch[CustomFilterSQL](CustomFilterSQL)


def get_relationship_info_from_field_metadata(
    field: FieldInfo,
) -> RelationshipInfo | None:
    return search_relationship_info.first(field)
