from datetime import datetime, UTC

from sqlalchemy import func
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import Mapped, mapped_column


class TimestampsMixin:
    @declared_attr
    def created_at(cls) -> Mapped[datetime]:
        return mapped_column(
            "created_at",
            default=datetime.utcnow,
            server_default=func.now(),
        )

    @declared_attr
    def modified_at(cls) -> Mapped[datetime]:
        return mapped_column(
            "modified_at",
            default=datetime.now(UTC),
            onupdate=datetime.now(UTC),
            server_onupdate=func.now(),
        )
