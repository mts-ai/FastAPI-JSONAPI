from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship

from examples.api_for_sqlalchemy.extensions.sqlalchemy import Base
from examples.api_for_sqlalchemy.utils.sqlalchemy.timestamps_mixin import TimestampsMixin

if TYPE_CHECKING:
    from examples.api_for_sqlalchemy.models import ParentToChildAssociation


class Child(Base, TimestampsMixin):
    __tablename__ = "right_table_children"

    name: Mapped[str] = mapped_column(nullable=False)
    parents: Mapped["ParentToChildAssociation"] = relationship(
        "ParentToChildAssociation",
        back_populates="child",
    )
