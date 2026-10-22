"""Database management and schema initialization for PocketDrop."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator
from app.config import settings


def get_db_path() -> Path:
    """Return the database path, ensuring parent directory exists."""
    settings.ensure_directories()
    return settings.DB_PATH


def init_db(db_path: Path = None) -> None:
    """Initialize SQLite tables and indexes."""
    target_path = db_path or get_db_path()
    with sqlite3.connect(target_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        
        # Files metadata table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                storage_key TEXT NOT NULL UNIQUE,
                size_bytes INTEGER NOT NULL,
                media_type TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_files_created ON files(created_at DESC);")

        # Text messages table (prepared for Phase 3)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS text_messages (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_text_created ON text_messages(created_at DESC);")
        conn.commit()


@contextmanager
def get_db(db_path: Path = None) -> Generator[sqlite3.Connection, None, None]:
    """Provide a transactional database connection, ensuring tables exist."""
    target_path = db_path or get_db_path()
    if not target_path.exists():
        init_db(target_path)
    conn = sqlite3.connect(target_path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
