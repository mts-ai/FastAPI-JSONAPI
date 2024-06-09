from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from examples.api_for_sqlalchemy.extensions.sqlalchemy import Base
from examples.api_for_sqlalchemy.utils.sqlalchemy.timestamps_mixin import TimestampsMixin

if TYPE_CHECKING:
    from .user import User


class Computer(Base, TimestampsMixin):
    __tablename__ = "computers"

    name: Mapped[str]
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    user: Mapped["User"] = relationship(back_populates="computers")

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id}, name={self.name!r}, user_id={self.user_id})"
