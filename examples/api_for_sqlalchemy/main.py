import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from examples.api_for_sqlalchemy import config
from examples.api_for_sqlalchemy.extensions.sqlalchemy import Base
from examples.api_for_sqlalchemy.urls import add_routes
from examples.api_for_sqlalchemy.util import register_static_docs_routes
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    await sqlalchemy_init()
    yield
    # shutdown
    # await db_helper.dispose()


def create_app(
    *,
    create_custom_static_urls: bool = False,
) -> FastAPI:
    app = FastAPI(
        title="FastAPI and SQLAlchemy",
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
        docs_url=None if create_custom_static_urls else "/docs",
        redoc_url=None if create_custom_static_urls else "/redoc",
    )
    if create_custom_static_urls:
        register_static_docs_routes(app)

    app.config = {"MAX_INCLUDE_DEPTH": 5}
    add_routes(app)
    init(app)
    return app


if __name__ == "__main__":
    uvicorn.run(
        "asgi:app",
        host="0.0.0.0",  # noqa: S104
        port=8082,
        reload=True,
        app_dir=str(CURRENT_DIR),
    )
