from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import (
    DeclarativeBase,
    sessionmaker,
    mapped_column,
    Mapped,
)

from examples.api_for_sqlalchemy import config


class Base(DeclarativeBase):
    id: Mapped[int] = mapped_column(primary_key=True)


def async_session() -> sessionmaker:
    engine = create_async_engine(url=make_url(config.SQLA_URI), echo=config.SQLA_ECHO)
    _async_session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    return _async_session


class Connector:
    @classmethod
    async def get_session(cls):
        """
        Get session as dependency

        :return:
        """
        sess = async_session()
        async with sess() as db_session:  # type: AsyncSession
            yield db_session
            await db_session.rollback()
