from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from examples.api_for_sqlalchemy.extensions.sqlalchemy import Base
from examples.api_for_sqlalchemy.utils.sqlalchemy.timestamps_mixin import TimestampsMixin

if TYPE_CHECKING:
    from .child import Child
    from .parent import Parent


class ParentToChildAssociation(Base, TimestampsMixin):
    __table_args__ = (
        # JSON:API requires `id` field on any model,
        # so we can't create a composite PK here
        # that's why we need to create this index
        Index(
            "ix_parent_child_association_unique",
            "parent_left_id",
            "child_right_id",
            unique=True,
        ),
    )

    __tablename__ = "parent_to_child_association_table"

    parent_left_id: Mapped[int] = mapped_column(
        ForeignKey("left_table_parents.id"),
    )
    child_right_id: Mapped[int] = mapped_column(
        ForeignKey("right_table_children.id"),
    )
    extra_data: Mapped[str] = mapped_column(String(50))
    parent: Mapped["Parent"] = relationship(
        back_populates="children",
        # primaryjoin="ParentToChildAssociation.parent_left_id == Parent.id",
    )
    child: Mapped["Child"] = relationship(
        back_populates="parents",
        # primaryjoin="ParentToChildAssociation.child_right_id == Child.id",
    )
