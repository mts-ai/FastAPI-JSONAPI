"""Factory call module."""

from examples.api_for_sqlalchemy.main import create_app

app = create_app(
    create_custom_static_urls=True,
)
