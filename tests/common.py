from os import getenv
from pathlib import Path


def sqla_uri():
    testing_db_url = getenv("TESTING_DB_URL")
    if not testing_db_url:
        db_dir = Path(__file__).resolve().parent
        testing_db_url = f"sqlite+aiosqlite:///{db_dir}/db.sqlite3"
    return testing_db_url


db_uri = sqla_uri()
IS_POSTGRES = "postgres" in db_uri
IS_SQLITE = "sqlite" in db_uri
