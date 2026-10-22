"""Tests for file listing, download, and deletion endpoints."""

import io
from fastapi.testclient import TestClient
from app.config import settings
from app.main import app
from app.security import get_or_create_auth_token

client = TestClient(app)


def test_file_lifecycle_listing_download_delete(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_DIR", tmp_path / "storage")
    monkeypatch.setattr(settings, "DB_PATH", tmp_path / "test.db")

    token = get_or_create_auth_token()
    headers = {"X-PocketDrop-Token": token}

    payload = b"PocketDrop end-to-end file transfer payload 1234567890"

    # 1. Upload
    up_res = client.post(
        "/api/uploads",
        files={"files": ("download_me.png", io.BytesIO(payload), "image/png")},
        headers=headers
    )
    assert up_res.status_code == 200
    file_id = up_res.json()["uploaded"][0]["id"]

    # 2. List
    list_res = client.get("/api/files", headers=headers)
    assert list_res.status_code == 200
    files = list_res.json()["files"]
    assert any(f["id"] == file_id for f in files)
    target = next(f for f in files if f["id"] == file_id)
    assert target["filename"] == "download_me.png"
    assert target["size_bytes"] == len(payload)

    # 3. Download
    down_res = client.get(f"/api/files/{file_id}", headers=headers)
    assert down_res.status_code == 200
    # Content matches byte-for-byte
    assert down_res.content == payload
    # Safe headers
    assert "attachment" in down_res.headers["content-disposition"]
    assert down_res.headers["x-content-type-options"] == "nosniff"

    # 4. Delete
    del_res = client.delete(f"/api/files/{file_id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"

    # 5. Subsequent download returns 404
    down_404 = client.get(f"/api/files/{file_id}", headers=headers)
    assert down_404.status_code == 404

    # 6. Listing no longer contains the file
    list_after = client.get("/api/files", headers=headers)
    assert not any(f["id"] == file_id for f in list_after.json()["files"])


def test_download_invalid_id_returns_404():
    token = get_or_create_auth_token()
    headers = {"X-PocketDrop-Token": token}
    res = client.get("/api/files/non-existent-uuid", headers=headers)
    assert res.status_code == 404
