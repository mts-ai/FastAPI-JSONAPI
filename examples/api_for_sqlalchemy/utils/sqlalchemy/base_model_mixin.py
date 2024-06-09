from datetime import datetime
from typing import Generic, List, TypeVar

from sqlalchemy import (
    delete,
    func,
    inspect,
    select,
)
from sqlalchemy.engine import Result
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import Mapped, mapped_column

from examples.api_for_sqlalchemy.extensions.sqlalchemy import Base

TypeBase = TypeVar("TypeBase", bound="Base")
Model = TypeVar("Model", Base, Base)


class BaseModelMixin(Generic[Model]):
    id: int

    @declared_attr
    def created_at(cls) -> Mapped[datetime]:
        """Дата создания записи"""
        return mapped_column(
            "created_at",
            default=datetime.utcnow,
            server_default=func.now(),
        )

    @declared_attr
    def modified_at(cls) -> Mapped[datetime]:
        """Дата изменения записи"""
        return mapped_column(
            "modified_at",
            default=datetime.utcnow,
            onupdate=datetime.utcnow,
            server_onupdate=func.now(),
        )

    def __repr__(self) -> str:
        return "<{}, pk: {}>".format(
            self.__class__.__name__,
            ", ".join(str(getattr(self, key.name)) for key in inspect(self.__class__).primary_key),
        )

    async def save(self, session: AsyncSession, commit: bool = True, flush: bool = False) -> "BaseModelMixin[Model]":
        has_pk: bool = all(getattr(self, key.name) for key in inspect(self.__class__).primary_key)
        if has_pk:
            await session.merge(self)
        else:
            session.add(self)
        if commit:
            await session.commit()
        elif flush:
            await session.flush()
        return self

    async def delete(self, session: AsyncSession, commit: bool = True) -> "BaseModelMixin[Model]":
        await session.execute(delete(self))
        if commit:
            await session.commit()
        return self

    @classmethod
    async def get_all(cls, session: AsyncSession) -> List[Model]:
        result = await session.execute(select(Model))
        return result.scalars().all()

    @classmethod
    async def get_by_id(cls, id_: int, session: AsyncSession) -> Model:
        stmt = select(cls).where(cls.id == id_)
        result: Result = await session.execute(stmt)
        return result.scalar_one()

    @classmethod
    async def get_or_none(cls, id_: int, session: AsyncSession) -> Model:
        stmt = select(cls).where(cls.id == id_)
        result: Result = await session.execute(stmt)
        return result.scalar_one_or_none()
