"""
Main module for w_mount service.

In module placed db initialization functions, app factory.
"""
import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
CURRENT_DIR = CURRENT_FILE.parent
PROJECT_DIR = CURRENT_DIR.parent.parent

sys.path.append(str(PROJECT_DIR))

import uvicorn
from fastapi import FastAPI
from tortoise import Tortoise

from examples.api_for_tortoise_orm.urls import add_routes


async def tortoise_init() -> None:
    # Here we create a SQLite DB using file "db.sqlite3"
    #  also specify the app name of "models"
    #  which contain models from "app.models"
    await Tortoise.init(
        db_url="sqlite://db.sqlite3",
        modules={"models": ["models.tortoise"]},
    )
    # Generate the schema
    await Tortoise.generate_schemas()


def create_app() -> FastAPI:
    """
    Create app factory.

    :return: app
    """
    app = FastAPI(
        title="FastAPI and Tortoise ORM",
        debug=True,
        openapi_url="/openapi.json",
        docs_url="/docs",
    )
    add_routes(app)
    app.on_event("startup")(tortoise_init)
    return app


if __name__ == "__main__":
    uvicorn.run(
        "asgi:app",
        host="0.0.0.0",
        port=8080,
        debug=True,
        reload=True,
        app_dir=str(CURRENT_DIR),
    )
