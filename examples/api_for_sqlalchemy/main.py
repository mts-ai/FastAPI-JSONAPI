"""
Main module for w_mount service.

In module placed db initialization functions, app factory.
"""
import sys
from pathlib import Path

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from examples.api_for_sqlalchemy.extensions.sqlalchemy import Base

CURRENT_FILE = Path(__file__).resolve()
CURRENT_DIR = CURRENT_FILE.parent
PROJECT_DIR = CURRENT_DIR.parent.parent

sys.path.append(str(PROJECT_DIR))

import uvicorn
from fastapi import FastAPI

from examples.api_for_sqlalchemy.urls import add_routes
from fastapi_jsonapi.schema import collect_app_orm_schemas
from fastapi_jsonapi.openapi import custom_openapi


async def sqlalchemy_init() -> None:
    uri = "sqlite+aiosqlite:///db.sqlite3"
    engine = create_async_engine(url=make_url(uri))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
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
    add_routes(app)
    app.on_event("startup")(sqlalchemy_init)
    custom_openapi(app, title="API for SQLAlchemy")
    collect_app_orm_schemas(app)
    return app


if __name__ == "__main__":
    uvicorn.run(
        "asgi:app",
        host="0.0.0.0",
        port=8082,
        reload=True,
        app_dir=str(CURRENT_DIR),
    )
