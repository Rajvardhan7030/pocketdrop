"""Tests for the StorageService and filesystem isolation."""

import io
import pytest
from pathlib import Path
from starlette.datastructures import UploadFile
from app.config import settings
from app.storage import (
    StorageNotFoundError,
    StoragePathEscapeError,
    StorageQuotaError,
    StorageService,
    sanitize_filename,
)


def test_sanitize_filename():
    assert sanitize_filename("normal.pdf") == "normal.pdf"
    assert sanitize_filename("../../../etc/passwd") == "passwd"
    assert sanitize_filename("..\\..\\windows\\system32\\cmd.exe") == "cmd.exe"
    assert sanitize_filename("test\0null.txt") == "testnull.txt"
    assert sanitize_filename("   spaced name.jpg   ") == "spaced name.jpg"
    assert sanitize_filename("") == "unnamed_file"
    assert sanitize_filename("...") == "unnamed_file"
    assert sanitize_filename("日本語ファイル.png") == "日本語ファイル.png"


@pytest.mark.anyio
async def test_save_and_retrieve_file(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_DIR", tmp_path / "storage")
    monkeypatch.setattr(settings, "DB_PATH", tmp_path / "test.db")
    service = StorageService(storage_dir=tmp_path / "storage")

    content = b"Binary file contents with non-ASCII: \xc3\xa9"
    upload = UploadFile(
        file=io.BytesIO(content),
        filename="report.pdf",
        headers={"content-type": "application/pdf"}
    )

    info = await service.save_upload(upload)
    assert info.filename == "report.pdf"
    assert info.size_bytes == len(content)

    # Verify disk path lookup
    disk_path, fetched_info = service.get_file_disk_path(info.id)
    assert disk_path.is_file()
    assert disk_path.read_bytes() == content
    assert fetched_info.id == info.id
    assert fetched_info.sha256 == info.sha256


@pytest.mark.anyio
async def test_duplicate_filenames_do_not_overwrite(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_DIR", tmp_path / "storage")
    monkeypatch.setattr(settings, "DB_PATH", tmp_path / "test.db")
    service = StorageService(storage_dir=tmp_path / "storage")

    f1 = UploadFile(file=io.BytesIO(b"version 1"), filename="document.txt")
    f2 = UploadFile(file=io.BytesIO(b"version 2"), filename="document.txt")

    info1 = await service.save_upload(f1)
    info2 = await service.save_upload(f2)

    assert info1.id != info2.id
    assert info1.filename == "document.txt"
    assert info2.filename == "document.txt"

    p1, _ = service.get_file_disk_path(info1.id)
    p2, _ = service.get_file_disk_path(info2.id)

    assert p1 != p2
    assert p1.read_bytes() == b"version 1"
    assert p2.read_bytes() == b"version 2"


@pytest.mark.anyio
async def test_per_file_quota_exceeded(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_DIR", tmp_path / "storage")
    monkeypatch.setattr(settings, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(settings, "MAX_FILE_SIZE_BYTES", 50)  # 50 bytes limit

    service = StorageService(storage_dir=tmp_path / "storage")
    oversized = UploadFile(file=io.BytesIO(b"A" * 100), filename="huge.bin")

    with pytest.raises(StorageQuotaError, match="exceeds the maximum allowed file size"):
        await service.save_upload(oversized)

    # Confirm no leftover temp files exist
    assert list((tmp_path / "storage").glob(".tmp_*")) == []


@pytest.mark.anyio
async def test_total_storage_quota_exceeded(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_DIR", tmp_path / "storage")
    monkeypatch.setattr(settings, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(settings, "MAX_TOTAL_STORAGE_BYTES", 80)

    service = StorageService(storage_dir=tmp_path / "storage")

    # Upload first file of 50 bytes
    f1 = UploadFile(file=io.BytesIO(b"A" * 50), filename="f1.dat")
    await service.save_upload(f1)

    # Upload second file of 40 bytes (total would be 90 > 80)
    f2 = UploadFile(file=io.BytesIO(b"B" * 40), filename="f2.dat")
    with pytest.raises(StorageQuotaError, match="Total storage quota exceeded"):
        await service.save_upload(f2)


@pytest.mark.anyio
async def test_delete_file(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_DIR", tmp_path / "storage")
    monkeypatch.setattr(settings, "DB_PATH", tmp_path / "test.db")
    service = StorageService(storage_dir=tmp_path / "storage")

    f = UploadFile(file=io.BytesIO(b"content"), filename="delete_me.txt")
    info = await service.save_upload(f)

    p, _ = service.get_file_disk_path(info.id)
    assert p.is_file()

    service.delete_file(info.id)
    assert not p.exists()

    with pytest.raises(StorageNotFoundError):
        service.get_file_disk_path(info.id)
