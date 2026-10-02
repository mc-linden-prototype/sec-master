"""The UI server: static files and the generated config.js."""

import json

from fastapi.testclient import TestClient

from casm.ui.server import create_ui_app


def ui_client(api_url: str = "http://127.0.0.1:9099") -> TestClient:
    return TestClient(create_ui_app(api_url=api_url))


def test_index_is_served_at_root_with_the_three_tabs() -> None:
    response = ui_client().get("/")
    assert response.status_code == 200
    for tab in ("Securities", "Reference Data", "Wiki"):
        assert tab in response.text


def test_config_js_tells_the_browser_where_the_api_is() -> None:
    response = ui_client("http://127.0.0.1:9099/").get("/config.js")
    assert response.headers["content-type"].startswith("text/javascript")
    assert response.text.strip() == 'window.CASM_API = "http://127.0.0.1:9099";'
    assert response.headers["cache-control"] == "no-store"


def test_config_js_value_is_a_safe_js_string() -> None:
    text = ui_client('http://x/"; alert(1); "').get("/config.js").text
    assert json.loads(text.split("= ", 1)[1].rstrip(";\n")) == 'http://x/"; alert(1); "'


def test_modules_and_styles_are_served() -> None:
    client = ui_client()
    for path in (
        "/js/main.js",
        "/js/securities.js",
        "/js/reference.js",
        "/js/wiki.js",
        "/styles.css",
    ):
        assert client.get(path).status_code == 200, path


def test_unknown_file_is_404_and_there_is_no_api_or_docs() -> None:
    client = ui_client()
    assert client.get("/nope.js").status_code == 404
    assert client.get("/docs").status_code == 404
