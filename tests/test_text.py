"""Tests for the text inbox transfer endpoints and SQLite persistence."""

import pytest
from fastapi.testclient import TestClient
from app.config import settings
from app.main import app
from app.security import get_or_create_auth_token

client = TestClient(app)


@pytest.fixture
def auth_headers():
    token = get_or_create_auth_token()
    return {"X-PocketDrop-Token": token}


def test_create_and_retrieve_text_snippet(auth_headers, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DB_PATH", tmp_path / "test_text.db")

    snippet = "Hello PocketDrop!\nThis has unicode: 🚀, quotes: \"hello 'world'\", and symbols: & < > /"

    # 1. Post text
    post_res = client.post(
        "/api/text",
        json={"content": snippet},
        headers=auth_headers
    )
    assert post_res.status_code == 200
    data = post_res.json()
    assert data["content"] == snippet
    text_id = data["id"]

    # 2. Retrieve list
    list_res = client.get("/api/text", headers=auth_headers)
    assert list_res.status_code == 200
    messages = list_res.json()["messages"]
    assert any(m["id"] == text_id for m in messages)
    found = next(m for m in messages if m["id"] == text_id)
    assert found["content"] == snippet


def test_text_snippet_html_characters_preserved_verbatim(auth_headers, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DB_PATH", tmp_path / "test_text.db")

    html_code = "<script>alert('xss')</script><img src=x onerror=alert(1)>"
    post_res = client.post(
        "/api/text",
        json={"content": html_code},
        headers=auth_headers
    )
    assert post_res.status_code == 200
    text_id = post_res.json()["id"]

    list_res = client.get("/api/text", headers=auth_headers)
    found = next(m for m in list_res.json()["messages"] if m["id"] == text_id)
    assert found["content"] == html_code


def test_text_snippet_empty_or_whitespace_rejected(auth_headers, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DB_PATH", tmp_path / "test_text.db")

    res_empty = client.post("/api/text", json={"content": ""}, headers=auth_headers)
    assert res_empty.status_code in (400, 422)

    res_spaces = client.post("/api/text", json={"content": "   \n\t  "}, headers=auth_headers)
    assert res_spaces.status_code == 400


def test_text_snippet_length_limit(auth_headers, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DB_PATH", tmp_path / "test_text.db")
    monkeypatch.setattr(settings, "MAX_TEXT_LENGTH", 50)

    oversized = "A" * 60
    res = client.post("/api/text", json={"content": oversized}, headers=auth_headers)
    assert res.status_code == 413
    assert "exceeds maximum allowed length" in res.json()["detail"]


def test_delete_text_snippet(auth_headers, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DB_PATH", tmp_path / "test_text.db")

    post_res = client.post("/api/text", json={"content": "Temporary note"}, headers=auth_headers)
    text_id = post_res.json()["id"]

    del_res = client.delete(f"/api/text/{text_id}", headers=auth_headers)
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"

    # Subsequent delete returns 404
    del_404 = client.delete(f"/api/text/{text_id}", headers=auth_headers)
    assert del_404.status_code == 404


def test_unauthorized_text_operations():
    unauth_client = TestClient(app)

    assert unauth_client.get("/api/text").status_code == 401
    assert unauth_client.post("/api/text", json={"content": "hi"}).status_code == 401
    assert unauth_client.delete("/api/text/some-id").status_code == 401
