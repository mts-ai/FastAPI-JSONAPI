import pytest
from sqlalchemy import AsyncAdaptedQueuePool
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    create_async_engine,
)

from tests.common import (
    sqla_uri,
)
from tests.models import Base


def create_engine():
    return create_async_engine(
        url=make_url(sqla_uri()),
        echo=False,
        pool_size=10,
        poolclass=AsyncAdaptedQueuePool,
    )


def get_async_session_maker() -> async_sessionmaker:
    engine = create_engine()
    return async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )


async def async_session_dependency():
    """
    Get session as dependency

    :return:
    """
    session_factory = get_async_session_maker()
    async with session_factory() as session:  # type: AsyncSession
        try:
            yield session
        finally:
            await session.rollback()


@pytest.fixture()
async def async_engine():
    return create_engine()


@pytest.fixture()
async def async_session(async_engine):
    session_factory = async_sessionmaker(
        bind=async_engine,
        expire_on_commit=False,
    )
    async with session_factory() as session:  # type: AsyncSession
        try:
            yield session
        finally:
            await session.rollback()


async def recreate_tables(engine):
    async with engine.begin() as connector:
        await connector.run_sync(Base.metadata.drop_all)
        await connector.run_sync(Base.metadata.create_all)


@pytest.fixture()
async def refresh_db(async_engine):
    await recreate_tables(async_engine)
