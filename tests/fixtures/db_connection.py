from pytest import fixture  # noqa PT013
from pytest_asyncio import fixture as async_fixture
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from tests.common import sqla_uri
from tests.models import Base


def get_async_sessionmaker() -> sessionmaker:
    engine = create_async_engine(url=make_url(sqla_uri()))
    _async_session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    return _async_session


async def async_session_dependency():
    """
    Get session as dependency

    :return:
    """
    session_maker = get_async_sessionmaker()
    async with session_maker() as db_session:  # type: AsyncSession
        yield db_session
        await db_session.rollback()


@async_fixture(scope="class")
async def async_engine():
    engine = create_async_engine(
        url=make_url(sqla_uri()),
        echo=False,
        # echo=True,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    return engine


@async_fixture(scope="class")
async def async_session_plain(async_engine):
    session = sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return session


@async_fixture(scope="class")
async def async_session(async_session_plain):
    async with async_session_plain() as session:
        yield session
