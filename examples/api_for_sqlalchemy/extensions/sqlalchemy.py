from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


Base = declarative_base()


def async_session() -> sessionmaker:
    uri = "sqlite+aiosqlite:///db.sqlite3"
    engine = create_async_engine(url=make_url(uri))
    _async_session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    return _async_session


class Connector:

    @classmethod
    async def get_session(cls):
        """
        Получение сессии к БД.

        :return:
        """
        async_session_ = async_session()
        async with async_session_() as db_session:
            async with db_session.begin():
                yield db_session
