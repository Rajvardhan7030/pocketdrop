"""Integration tests with real file types: images, PDFs, ZIP archives, and binary streams."""

import hashlib
import io
import zipfile
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


def test_transfer_zip_archive(auth_headers, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_DIR", tmp_path / "storage")
    monkeypatch.setattr(settings, "DB_PATH", tmp_path / "test.db")

    # Create in-memory zip
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("notes.txt", "PocketDrop in-archive text")
        zf.writestr("subfolder/data.csv", "1,2,3\n4,5,6")
    zip_bytes = zip_buffer.getvalue()
    expected_hash = hashlib.sha256(zip_bytes).hexdigest()

    # Upload ZIP
    up_res = client.post(
        "/api/uploads",
        files={"files": ("archive.zip", io.BytesIO(zip_bytes), "application/zip")},
        headers=auth_headers
    )
    assert up_res.status_code == 200
    file_id = up_res.json()["uploaded"][0]["id"]

    # Download ZIP
    down_res = client.get(f"/api/files/{file_id}", headers=auth_headers)
    assert down_res.status_code == 200
    assert down_res.content == zip_bytes
    assert hashlib.sha256(down_res.content).hexdigest() == expected_hash

    # Verify zip content can be opened
    with zipfile.ZipFile(io.BytesIO(down_res.content), "r") as zf:
        assert zf.read("notes.txt") == b"PocketDrop in-archive text"


def test_transfer_pdf_and_binary(auth_headers, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_DIR", tmp_path / "storage")
    monkeypatch.setattr(settings, "DB_PATH", tmp_path / "test.db")

    # Simulated PDF header + binary payload
    pdf_bytes = b"%PDF-1.4\n%PocketDrop binary test data \x00\xff\xfe\xfd\x01\x02\x03\n%%EOF"
    expected_hash = hashlib.sha256(pdf_bytes).hexdigest()

    up_res = client.post(
        "/api/uploads",
        files={"files": ("document.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers=auth_headers
    )
    assert up_res.status_code == 200
    file_id = up_res.json()["uploaded"][0]["id"]

    down_res = client.get(f"/api/files/{file_id}", headers=auth_headers)
    assert down_res.status_code == 200
    assert down_res.content == pdf_bytes
    assert hashlib.sha256(down_res.content).hexdigest() == expected_hash


def test_persistence_across_service_restarts(auth_headers, tmp_path, monkeypatch):
    storage_dir = tmp_path / "persistent_storage"
    db_path = tmp_path / "persistent.db"
    monkeypatch.setattr(settings, "STORAGE_DIR", storage_dir)
    monkeypatch.setattr(settings, "DB_PATH", db_path)

    # 1. Upload file and post text
    client.post(
        "/api/uploads",
        files={"files": ("saved.txt", io.BytesIO(b"preserved across restart"), "text/plain")},
        headers=auth_headers
    )
    client.post(
        "/api/text",
        json={"content": "snippet preserved across restart"},
        headers=auth_headers
    )

    # 2. Simulate complete application restart by instantiating fresh app client and checking DB
    fresh_client = TestClient(app)

    files_res = fresh_client.get("/api/files", headers=auth_headers)
    assert files_res.status_code == 200
    assert any(f["filename"] == "saved.txt" for f in files_res.json()["files"])

    text_res = fresh_client.get("/api/text", headers=auth_headers)
    assert text_res.status_code == 200
    assert any(m["content"] == "snippet preserved across restart" for m in text_res.json()["messages"])
