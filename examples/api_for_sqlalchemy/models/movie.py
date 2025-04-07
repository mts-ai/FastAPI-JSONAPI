from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    ForeignKey,
    Identity,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from examples.api_for_sqlalchemy.models.base import Base

if TYPE_CHECKING:
    from examples.api_for_sqlalchemy.models.age_rating import AgeRating


class Movie(Base):
    __tablename__ = "movie"

    id: Mapped[int] = mapped_column(
        Integer,
        Identity(always=True),
        primary_key=True,
        autoincrement=True,
    )
    title: Mapped[str] = mapped_column(
        String(120),
        index=True,
    )
    description: Mapped[str] = mapped_column(
        Text,
        default="",
        server_default="",
    )
    age_rating: Mapped[Optional[str]] = mapped_column(
        ForeignKey(
            "age_rating.name",
            ondelete="SET NULL",
        ),
    )
    age_rating_obj: Mapped["AgeRating"] = relationship(
        back_populates="movies",
    )

    def __str__(self) -> str:
        return self.title

    def __repr__(self) -> str:
        return f"Movie(id={self.id}, title={self.title!r})"
