"""Openapi handler."""

from typing import (
    Any,
    Dict,
    Optional,
)

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


def custom_openapi(app: FastAPI, title: Optional[str] = None) -> None:
    """Add custom implementation for swagger implementation."""

    def openapi() -> Dict[Any, Any]:
        """Openapi schema."""
        if app.openapi_schema:
            return app.openapi_schema
        openapi_schema = get_openapi(
            title=title or "FastAPI-JSONAPI",
            version="2.5.0",
            description="",
            routes=app.routes,
        )
        # картинка по адресу недоступна
        # openapi_schema["info"]["x-logo"] = {
        #     "url": "https://static.ssl.mts.ru/mts_rf/static/20201102.1/Styles/Promo/i/header/logo.svg",
        # }
        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = openapi
