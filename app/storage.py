"""Dedicated file storage service with streaming, atomic writes, and quota enforcement."""

import hashlib
import os
import re
import unicodedata
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, List, Optional, Tuple
from fastapi import UploadFile

from app.config import settings
from app.db import get_db, init_db

# Chunk size for streaming writes (64 KB)
CHUNK_SIZE = 64 * 1024


class StorageError(Exception):
    """Base storage error."""
    pass


class StorageQuotaError(StorageError):
    """Raised when file size or total storage quota is exceeded."""
    pass


class StorageNotFoundError(StorageError):
    """Raised when a requested file is not found."""
    pass


class StoragePathEscapeError(StorageError):
    """Raised when a path escape/traversal is detected."""
    pass


@dataclass
class StoredFileInfo:
    id: str
    filename: str
    size_bytes: int
    media_type: str
    sha256: str
    created_at: str


def sanitize_filename(raw_name: Optional[str]) -> str:
    """
    Sanitize client-provided filename for safe display.
    Removes path separators, null bytes, and non-printable control characters.
    Preserves normal UTF-8 characters for international languages.
    """
    if not raw_name:
        return "unnamed_file"

    # Normalize Unicode
    name = unicodedata.normalize("NFKC", raw_name)

    # Strip directory components (both / and \)
    name = os.path.basename(name.replace("\\", "/"))

    # Remove null bytes and control characters
    name = "".join(c for c in name if c.isprintable() and c != "\0")

    # Strip leading/trailing whitespace and dots
    name = name.strip(" .")

    if not name:
        return "unnamed_file"

    # Cap display length to 255 characters
    return name[:255]


class StorageService:
    """Encapsulates all disk storage and database metadata operations."""

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = (storage_dir or settings.STORAGE_DIR).resolve()
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        init_db()

    def get_current_total_storage(self) -> int:
        """Calculate total bytes occupied by stored files recorded in SQLite."""
        with get_db() as conn:
            cursor = conn.execute("SELECT COALESCE(SUM(size_bytes), 0) FROM files")
            row = cursor.fetchone()
            return int(row[0]) if row else 0

    async def save_upload(self, upload_file: UploadFile) -> StoredFileInfo:
        """
        Stream an incoming file upload directly to disk using an atomic temporary file.
        Enforces per-file and total storage quotas on the fly.
        Computes SHA-256 checksum during streaming.
        """
        file_id = str(uuid.uuid4())
        storage_key = f"{file_id}.dat"
        temp_path = self.storage_dir / f".tmp_{file_id}"
        final_path = self.storage_dir / storage_key

        display_filename = sanitize_filename(upload_file.filename)
        # Treat MIME type as advisory metadata only
        media_type = (upload_file.content_type or "application/octet-stream").strip()[:100]

        hasher = hashlib.sha256()
        total_written = 0
        current_total = self.get_current_total_storage()

        try:
            with open(temp_path, "wb") as f_out:
                while True:
                    chunk = await upload_file.read(CHUNK_SIZE)
                    if not chunk:
                        break

                    chunk_len = len(chunk)
                    # 1. Per-file quota check
                    if total_written + chunk_len > settings.MAX_FILE_SIZE_BYTES:
                        raise StorageQuotaError(
                            f"File '{display_filename}' exceeds the maximum allowed file size "
                            f"of {settings.MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB."
                        )

                    # 2. Total storage quota check
                    if current_total + total_written + chunk_len > settings.MAX_TOTAL_STORAGE_BYTES:
                        raise StorageQuotaError(
                            "Total storage quota exceeded. Please delete some files before uploading more."
                        )

                    f_out.write(chunk)
                    hasher.update(chunk)
                    total_written += chunk_len

            # Atomically commit the temporary file
            temp_path.replace(final_path)

        except Exception:
            # Clean up partial temporary file on failure
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass
            raise

        sha256_hash = hasher.hexdigest()

        # Insert metadata into SQLite
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO files (id, filename, storage_key, size_bytes, media_type, sha256)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (file_id, display_filename, storage_key, total_written, media_type, sha256_hash)
            )
            cursor = conn.execute("SELECT created_at FROM files WHERE id = ?", (file_id,))
            created_at = cursor.fetchone()["created_at"]

        return StoredFileInfo(
            id=file_id,
            filename=display_filename,
            size_bytes=total_written,
            media_type=media_type,
            sha256=sha256_hash,
            created_at=str(created_at)
        )

    def list_files(self) -> List[StoredFileInfo]:
        """Return all authorized shared files sorted by creation date descending."""
        with get_db() as conn:
            cursor = conn.execute(
                """
                SELECT id, filename, size_bytes, media_type, sha256, created_at
                FROM files
                ORDER BY created_at DESC
                """
            )
            rows = cursor.fetchall()
            return [
                StoredFileInfo(
                    id=row["id"],
                    filename=row["filename"],
                    size_bytes=row["size_bytes"],
                    media_type=row["media_type"],
                    sha256=row["sha256"],
                    created_at=str(row["created_at"])
                )
                for row in rows
            ]

    def get_file_record(self, file_id: str) -> StoredFileInfo:
        """Lookup file metadata by internal ID."""
        with get_db() as conn:
            cursor = conn.execute(
                """
                SELECT id, filename, size_bytes, media_type, sha256, created_at
                FROM files
                WHERE id = ?
                """,
                (file_id,)
            )
            row = cursor.fetchone()
            if not row:
                raise StorageNotFoundError(f"File with ID '{file_id}' not found.")
            return StoredFileInfo(
                id=row["id"],
                filename=row["filename"],
                size_bytes=row["size_bytes"],
                media_type=row["media_type"],
                sha256=row["sha256"],
                created_at=str(row["created_at"])
            )

    def get_file_disk_path(self, file_id: str) -> Tuple[Path, StoredFileInfo]:
        """
        Resolve the real filesystem path for a file by its opaque ID,
        asserting that the resolved path is strictly within the dedicated storage directory.
        """
        info = self.get_file_record(file_id)

        with get_db() as conn:
            cursor = conn.execute("SELECT storage_key FROM files WHERE id = ?", (file_id,))
            row = cursor.fetchone()
            storage_key = row["storage_key"]

        file_path = (self.storage_dir / storage_key).resolve()

        # Path traversal guard: must be strictly inside storage_dir
        if not str(file_path).startswith(str(self.storage_dir)):
            raise StoragePathEscapeError("Path escape attempt detected.")

        if not file_path.is_file():
            raise StorageNotFoundError(f"File '{file_id}' data missing on disk.")

        return file_path, info

    def delete_file(self, file_id: str) -> None:
        """
        Delete a file from disk and its metadata record from the database.
        """
        with get_db() as conn:
            cursor = conn.execute("SELECT storage_key FROM files WHERE id = ?", (file_id,))
            row = cursor.fetchone()
            if not row:
                raise StorageNotFoundError(f"File with ID '{file_id}' not found.")
            storage_key = row["storage_key"]

            # Remove DB record first in transaction
            conn.execute("DELETE FROM files WHERE id = ?", (file_id,))

        # Remove physical file from disk
        file_path = (self.storage_dir / storage_key).resolve()
        if str(file_path).startswith(str(self.storage_dir)) and file_path.exists():
            try:
                file_path.unlink()
            except OSError as e:
                logger.warning("Failed to unlink deleted file %s: %s", file_path, e)
