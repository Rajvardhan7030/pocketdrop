"""Tests for the /api/status endpoint."""

from fastapi.testclient import TestClient
from app import __version__
from app.main import app

client = TestClient(app)


def test_status_endpoint_success():
    """Verify GET /api/status returns 200 and expected non-sensitive payload."""
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ok"
    assert data["app"] == "PocketDrop"
    assert data["version"] == __version__


def test_status_endpoint_does_not_leak_secrets():
    """
    Verify status response does not expose tokens, paths, file listings,
    passwords, or internal secrets.
    """
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()

    forbidden_keys = {
        "token", "auth", "secret", "password", "key",
        "files", "storage", "path", "ip", "credentials"
    }
    for key in forbidden_keys:
        assert key not in data, f"Sensitive key '{key}' found in status response"
