from os import getenv

SQLA_URI = getenv("SQLA_URI", "sqlite+aiosqlite:///./db.sqlite3")
SQLA_ECHO = getenv("SQLA_ECHO", "0") == "1"
