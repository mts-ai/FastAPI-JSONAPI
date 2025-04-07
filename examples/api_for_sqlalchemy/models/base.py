from typing import Any, ClassVar

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class BaseMetadata(DeclarativeBase):
    __table_args__: ClassVar[dict[str, Any]] = {
        "extend_existing": True,
    }


class Base(BaseMetadata):
    __abstract__ = True

    id: Mapped[int] = mapped_column(primary_key=True)
