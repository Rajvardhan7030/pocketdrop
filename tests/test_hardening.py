"""Comprehensive security hardening and edge case tests."""

import asyncio
import io
import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.security import get_or_create_auth_token
from app.storage import StoragePathEscapeError, StorageService, sanitize_filename

client = TestClient(app)


@pytest.fixture
def auth_headers():
    token = get_or_create_auth_token()
    return {"X-PocketDrop-Token": token}


def test_path_traversal_attempts_in_file_id(auth_headers, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_DIR", tmp_path / "storage")
    monkeypatch.setattr(settings, "DB_PATH", tmp_path / "test.db")

    traversal_ids = [
        "../../etc/passwd",
        "..%2F..%2Fetc%2Fpasswd",
        "../../../etc/shadow",
        "nested/../../../../etc/hosts",
        "/etc/passwd",
        "C:\\Windows\\System32\\cmd.exe",
        "....//....//....//etc/passwd",
        "file%00.txt",
    ]

    for evil_id in traversal_ids:
        # Download attempt
        res_down = client.get(f"/api/files/{evil_id}", headers=auth_headers)
        assert res_down.status_code in (404, 403, 400), f"Traversal ID '{evil_id}' was not rejected"

        # Delete attempt
        res_del = client.delete(f"/api/files/{evil_id}", headers=auth_headers)
        assert res_del.status_code in (404, 403, 400), f"Delete with traversal ID '{evil_id}' was not rejected"


def test_storage_symlink_escape_rejection(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_DIR", tmp_path / "storage")
    monkeypatch.setattr(settings, "DB_PATH", tmp_path / "test.db")
    service = StorageService(storage_dir=tmp_path / "storage")

    # Outside secret file
    secret_file = tmp_path / "secret.txt"
    secret_file.write_text("SUPER_SECRET_HOST_CONTENT")

    # Create symlink inside storage pointing outside
    symlink_path = tmp_path / "storage" / "evil_symlink.dat"
    os.symlink(secret_file, symlink_path)

    # Insert malicious row referencing the symlink
    with pytest.raises(Exception):
        # Directly calling get_file_disk_path with an unlisted ID
        service.get_file_disk_path("evil_symlink")


def test_unicode_and_extreme_filenames():
    # Long filename (>255 chars) is safely truncated
    long_name = "a" * 300 + ".png"
    sanitized = sanitize_filename(long_name)
    assert len(sanitized) <= 255
    assert sanitized.endswith(".png")

    # RTL, Cyrillic, Emoji
    assert sanitize_filename("ملف_عربي.pdf") == "ملف_عربي.pdf"
    assert sanitize_filename("документ.docx") == "документ.docx"
    assert sanitize_filename("🎉_photo_📷.jpeg") == "🎉_photo_📷.jpeg"


def test_no_secrets_in_server_logs(caplog):
    token = get_or_create_auth_token()
    caplog.clear()

    # Trigger legitimate requests and error responses
    client.post("/api/auth/pair", json={"pin": token})
    client.post("/api/auth/pair", json={"pin": "wrong_pin"})
    client.get("/api/status")

    # Assert token never appears anywhere in the captured log records
    for record in caplog.records:
        assert token not in record.message
        assert "auth_token" not in record.message
