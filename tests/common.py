from os import getenv
from pathlib import Path


def sqla_uri():
    testing_db_url = getenv("TESTING_DB_URL")
    if not testing_db_url:
        db_dir = Path(__file__).resolve().parent
        testing_db_url = f"sqlite+aiosqlite:///{db_dir}/db.sqlite3"
    return testing_db_url


def is_postgres_tests() -> bool:
    return "postgres" in sqla_uri()
