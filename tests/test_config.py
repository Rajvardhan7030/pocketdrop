"""Tests for PocketDrop configuration module."""

import pytest
from pathlib import Path
from app.config import Settings


def test_default_settings():
    settings = Settings()
    assert settings.PORT == 8000
    assert settings.HOST == "127.0.0.1"
    assert settings.MAX_FILE_SIZE_BYTES == 500 * 1024 * 1024
    assert settings.MAX_TOTAL_STORAGE_BYTES == 10 * 1024 * 1024 * 1024
    assert settings.MAX_TEXT_LENGTH == 10000
    assert settings.DATA_DIR.name == "data"
    assert settings.STORAGE_DIR == settings.DATA_DIR / "storage"
    assert settings.DB_PATH == settings.DATA_DIR / "pocketdrop.db"


def test_custom_data_dir(tmp_path):
    custom_dir = tmp_path / "custom_data"
    settings = Settings(data_dir=custom_dir)
    assert settings.DATA_DIR == custom_dir
    assert settings.STORAGE_DIR == custom_dir / "storage"
    assert settings.DB_PATH == custom_dir / "pocketdrop.db"

    # Verify directory creation
    assert not custom_dir.exists()
    settings.ensure_directories()
    assert custom_dir.is_dir()
    assert settings.STORAGE_DIR.is_dir()


def test_invalid_port():
    with pytest.raises(ValueError, match="Port must be between 1 and 65535"):
        Settings(port=0)

    with pytest.raises(ValueError, match="Port must be between 1 and 65535"):
        Settings(port=70000)


def test_invalid_limits():
    with pytest.raises(ValueError, match="max_file_size_bytes must be positive"):
        Settings(max_file_size_bytes=0)

    with pytest.raises(ValueError, match="max_total_storage_bytes must be positive"):
        Settings(max_total_storage_bytes=-1)

    with pytest.raises(ValueError, match="max_text_length must be positive"):
        Settings(max_text_length=0)


def test_env_override(monkeypatch, tmp_path):
    test_data = tmp_path / "env_data"
    monkeypatch.setenv("POCKETDROP_DATA_DIR", str(test_data))
    monkeypatch.setenv("POCKETDROP_PORT", "9090")
    monkeypatch.setenv("POCKETDROP_HOST", "192.168.1.50")
    monkeypatch.setenv("POCKETDROP_MAX_FILE_SIZE_BYTES", "1048576")
    monkeypatch.setenv("POCKETDROP_AUTH_TOKEN", "secret123")

    settings = Settings()
    assert settings.DATA_DIR == test_data
    assert settings.PORT == 9090
    assert settings.HOST == "192.168.1.50"
    assert settings.MAX_FILE_SIZE_BYTES == 1048576
    assert settings.AUTH_TOKEN == "secret123"
