from typing import Optional

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from examples.api_for_sqlalchemy import config

Base = declarative_base()


def async_session() -> sessionmaker:
    engine = create_async_engine(url=make_url(config.SQLA_URI), echo=config.SQLA_ECHO)
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
