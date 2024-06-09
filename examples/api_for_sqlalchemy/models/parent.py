from typing import TYPE_CHECKING

from sqlalchemy.orm import (
    Mapped,
    relationship,
)

from examples.api_for_sqlalchemy.extensions.sqlalchemy import Base
from examples.api_for_sqlalchemy.utils.sqlalchemy.timestamps_mixin import TimestampsMixin

if TYPE_CHECKING:
    from examples.api_for_sqlalchemy.models import ParentToChildAssociation


class Parent(Base, TimestampsMixin):
    __tablename__ = "left_table_parents"

    name: Mapped[str]
    children: Mapped[list["ParentToChildAssociation"]] = relationship(
        back_populates="parent",
    )
