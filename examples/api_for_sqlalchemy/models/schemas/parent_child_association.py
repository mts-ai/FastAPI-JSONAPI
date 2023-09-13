from typing import TYPE_CHECKING

from fastapi_jsonapi.schema_base import BaseModel, Field, RelationshipInfo

if TYPE_CHECKING:
    from .child import ChildSchema
    from .parent import ParentSchema


class ParentToChildAssociationSchema(BaseModel):
    id: int
    extra_data: str

    parent: "ParentSchema" = Field(
        default=None,
        relationship=RelationshipInfo(
            resource_type="parent",
        ),
    )

    child: "ChildSchema" = Field(
        default=None,
        relationship=RelationshipInfo(
            resource_type="child",
        ),
    )
