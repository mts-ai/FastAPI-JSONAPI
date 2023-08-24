from pathlib import Path

import uvicorn

from tests.fixtures.app import add_routers, build_app_plain

CURRENT_FILE = Path(__file__).resolve()
CURRENT_DIR = CURRENT_FILE.parent


app = build_app_plain()
add_routers(app)


if __name__ == "__main__":
    uvicorn.run(
        "debug_app:app",
        host="0.0.0.0",
        port=8082,
        reload=True,
        app_dir=str(CURRENT_DIR),
    )
