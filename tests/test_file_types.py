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


def test_transfer_video_file(auth_headers, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_DIR", tmp_path / "storage")
    monkeypatch.setattr(settings, "DB_PATH", tmp_path / "test.db")

    # Simulated MP4 container header + binary stream
    mp4_header = b"\x00\x00\x00 ftypisom\x00\x00\x02\x00isomiso2avc1mp41"
    video_bytes = mp4_header + (b"\x12\x34\x56\x78" * 50000)  # ~200 KB
    expected_hash = hashlib.sha256(video_bytes).hexdigest()

    up_res = client.post(
        "/api/uploads",
        files={"files": ("clip.mp4", io.BytesIO(video_bytes), "video/mp4")},
        headers=auth_headers
    )
    assert up_res.status_code == 200
    file_id = up_res.json()["uploaded"][0]["id"]

    down_res = client.get(f"/api/files/{file_id}", headers=auth_headers)
    assert down_res.status_code == 200
    assert down_res.content == video_bytes
    assert hashlib.sha256(down_res.content).hexdigest() == expected_hash
    assert "attachment" in down_res.headers["content-disposition"]


def test_concurrent_uploads(auth_headers, tmp_path, monkeypatch):
    import concurrent.futures
    from app.db import init_db

    monkeypatch.setattr(settings, "STORAGE_DIR", tmp_path / "storage")
    monkeypatch.setattr(settings, "DB_PATH", tmp_path / "test.db")
    init_db(tmp_path / "test.db")

    def upload_worker(index):
        worker_client = TestClient(app)
        data = f"concurrent worker payload {index}".encode("utf-8")
        res = worker_client.post(
            "/api/uploads",
            files={"files": (f"worker_{index}.txt", io.BytesIO(data), "text/plain")},
            headers=auth_headers
        )
        return res.status_code, res.json()["uploaded"][0]["id"]

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(upload_worker, i) for i in range(4)]
        results = [f.result() for f in futures]

    assert all(code == 200 for code, _ in results)
    uploaded_ids = [uid for _, uid in results]
    assert len(set(uploaded_ids)) == 4


@pytest.mark.anyio
async def test_interrupted_upload_cleans_up_temp_file(tmp_path, monkeypatch):
    from starlette.datastructures import UploadFile
    from app.storage import StorageService

    monkeypatch.setattr(settings, "STORAGE_DIR", tmp_path / "storage")
    monkeypatch.setattr(settings, "DB_PATH", tmp_path / "test.db")
    service = StorageService(storage_dir=tmp_path / "storage")

    class FaultyStream:
        def __init__(self):
            self.calls = 0

        def read(self, chunk_size=-1):
            self.calls += 1
            if self.calls == 1:
                return b"First chunk succeeds"
            raise ConnectionResetError("Client disconnected unexpectedly")

    faulty_file = UploadFile(file=FaultyStream(), filename="interrupted.dat")

    with pytest.raises(ConnectionResetError):
        await service.save_upload(faulty_file)

    # Verify no dangling temporary files remain
    temp_files = list((tmp_path / "storage").glob(".tmp_*"))
    assert temp_files == []

