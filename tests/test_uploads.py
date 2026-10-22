"""Tests for file upload endpoints and validation."""

import hashlib
import io
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


def test_upload_single_file(auth_headers, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_DIR", tmp_path / "storage")
    monkeypatch.setattr(settings, "DB_PATH", tmp_path / "test.db")

    data = b"Hello, PocketDrop upload test!"
    expected_hash = hashlib.sha256(data).hexdigest()

    response = client.post(
        "/api/uploads",
        files={"files": ("sample.txt", io.BytesIO(data), "text/plain")},
        headers=auth_headers
    )
    assert response.status_code == 200
    res_data = response.json()
    assert "uploaded" in res_data
    assert len(res_data["uploaded"]) == 1

    item = res_data["uploaded"][0]
    assert item["filename"] == "sample.txt"
    assert item["size_bytes"] == len(data)
    assert item["sha256"] == expected_hash


def test_upload_multiple_files(auth_headers, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_DIR", tmp_path / "storage")
    monkeypatch.setattr(settings, "DB_PATH", tmp_path / "test.db")

    f1_data = b"first file data"
    f2_data = b"second file data"

    files = [
        ("files", ("file1.txt", io.BytesIO(f1_data), "text/plain")),
        ("files", ("file2.txt", io.BytesIO(f2_data), "text/plain")),
    ]

    response = client.post("/api/uploads", files=files, headers=auth_headers)
    assert response.status_code == 200
    uploaded = response.json()["uploaded"]
    assert len(uploaded) == 2
    assert {u["filename"] for u in uploaded} == {"file1.txt", "file2.txt"}


def test_upload_unauthorized():
    response = client.post(
        "/api/uploads",
        files={"files": ("test.txt", io.BytesIO(b"data"), "text/plain")}
    )
    assert response.status_code == 401


def test_upload_oversized_file(auth_headers, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_DIR", tmp_path / "storage")
    monkeypatch.setattr(settings, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(settings, "MAX_FILE_SIZE_BYTES", 100)  # 100 bytes limit

    oversized_data = b"X" * 200
    response = client.post(
        "/api/uploads",
        files={"files": ("big.bin", io.BytesIO(oversized_data), "application/octet-stream")},
        headers=auth_headers
    )
    assert response.status_code == 413
    assert "exceeds the maximum allowed file size" in response.json()["detail"]
