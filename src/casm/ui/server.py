"""Serves the web UI's static files and a generated config.js that tells the browser where the API is."""

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

UI_DIR: Path = Path(__file__).resolve().parent


def create_ui_app(*, api_url: str, ui_dir: Path = UI_DIR) -> FastAPI:
    """Build the UI app.

    Args:
        api_url: The API's base address, for example `http://127.0.0.1:9099`.
        ui_dir: Folder holding index.html, styles.css and js/.
    """
    app: FastAPI = FastAPI(
        title="C.A.S.M UI", docs_url=None, redoc_url=None, openapi_url=None
    )

    @app.get("/config.js", include_in_schema=False)
    async def config() -> Response:
        return Response(
            content=f"window.CASM_API = {json.dumps(api_url.rstrip('/'))};\n",
            media_type="text/javascript",
            headers={"Cache-Control": "no-store"},
        )

    app.mount("/", StaticFiles(directory=ui_dir, html=True), name="ui")
    return app
