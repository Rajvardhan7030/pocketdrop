"""Tests for the dashboard page and static asset serving."""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_dashboard_serves_html():
    """Verify GET / returns 200 with HTML content."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "PocketDrop" in response.text
    assert "/static/style.css" in response.text
    assert "/static/app.js" in response.text


def test_static_assets_available():
    """Verify static CSS and JS are served correctly."""
    css_res = client.get("/static/style.css")
    assert css_res.status_code == 200
    assert "text/css" in css_res.headers["content-type"]

    js_res = client.get("/static/app.js")
    assert js_res.status_code == 200
    assert "javascript" in js_res.headers["content-type"]


def test_static_isolation_from_storage():
    """Verify that storage or parent paths cannot be accessed via static mount."""
    res = client.get("/static/../data/storage")
    assert res.status_code in (404, 400)

    res2 = client.get("/static/storage")
    assert res2.status_code == 404
