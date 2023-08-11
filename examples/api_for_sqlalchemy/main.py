"""
Main module for w_mount service.

In module placed db initialization functions, app factory.
"""
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from examples.api_for_sqlalchemy import config
from examples.api_for_sqlalchemy.extensions.sqlalchemy import Base
from examples.api_for_sqlalchemy.urls import add_routes
from fastapi_jsonapi import init

CURRENT_FILE = Path(__file__).resolve()
CURRENT_DIR = CURRENT_FILE.parent
PROJECT_DIR = CURRENT_DIR.parent.parent

sys.path.append(str(PROJECT_DIR))


async def sqlalchemy_init() -> None:
    engine = create_async_engine(url=make_url(config.SQLA_URI), echo=config.SQLA_ECHO)
    async with engine.begin() as conn:
        # We don't want to drop tables on each app restart!
        # await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


def create_app() -> FastAPI:
    """
    Create app factory.

    :return: app
    """
    app = FastAPI(
        title="FastAPI and SQLAlchemy",
        debug=True,
        openapi_url="/openapi.json",
        docs_url="/docs",
    )
    app.config = {"MAX_INCLUDE_DEPTH": 5}
    add_routes(app)
    app.on_event("startup")(sqlalchemy_init)
    init(app)
    return app


if __name__ == "__main__":
    uvicorn.run(
        "asgi:app",
        host="0.0.0.0",
        port=8082,
        reload=True,
        app_dir=str(CURRENT_DIR),
    )
