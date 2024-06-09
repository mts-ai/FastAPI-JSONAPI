from os import getenv
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.engine import Engine


def sqla_db_filepath():
    return Path(__file__).resolve().parent / "db.sqlite3"


def sqla_uri():
    testing_db_url = getenv("TESTING_DB_URL")
    if not testing_db_url:
        testing_db_url = f"sqlite+aiosqlite:///{sqla_db_filepath()}"
    return testing_db_url


def is_postgres_tests() -> bool:
    return "postgres" in sqla_uri()


def is_sqlite_tests() -> bool:
    return "sqlite" in sqla_uri()


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """
    https://docs.sqlalchemy.org/en/14/dialects/sqlite.html#foreign-key-support
    """
    if is_sqlite_tests():
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
