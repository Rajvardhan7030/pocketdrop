"""Tests for authentication, pairing, and CSRF security."""

import pytest
from fastapi.testclient import TestClient
from app.config import settings
from app.main import app
from app.security import (
    create_session,
    get_or_create_auth_token,
    validate_session,
    verify_pairing_token,
)

client = TestClient(app)


def test_pairing_token_verification():
    token = get_or_create_auth_token()
    assert verify_pairing_token(token) is True
    # Test spaces and hyphens commonly entered on mobile
    if token.isdigit() and len(token) == 6:
        spaced = f"{token[:3]} {token[3:]}"
        hyphenated = f"{token[:3]}-{token[3:]}"
        padded = f"  {token}  "
        assert verify_pairing_token(spaced) is True
        assert verify_pairing_token(hyphenated) is True
        assert verify_pairing_token(padded) is True

    assert verify_pairing_token("wrong-pin") is False
    assert verify_pairing_token("") is False


def test_custom_token_and_force_new(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path / "data")
    custom = get_or_create_auth_token(custom_token="my-secret-pin-123")
    assert custom == "my-secret-pin-123"
    assert verify_pairing_token("my-secret-pin-123") is True

    # Force new generates a 6 digit PIN
    new_pin = get_or_create_auth_token(force_new=True)
    assert new_pin.isdigit()
    assert len(new_pin) == 6
    assert verify_pairing_token(new_pin) is True


def test_pair_endpoint_success():
    token = get_or_create_auth_token()
    response = client.post("/api/auth/pair", json={"pin": token})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "csrf_token" in data
    assert "pocketdrop_session" in response.cookies


def test_pair_endpoint_invalid_pin():
    response = client.post("/api/auth/pair", json={"pin": "000000_invalid"})
    assert response.status_code == 401
    assert "pocketdrop_session" not in response.cookies


def test_protected_routes_require_auth():
    # Use fresh client without cookies
    unauth_client = TestClient(app)

    # Attempt to list files without auth
    res_list = unauth_client.get("/api/files")
    assert res_list.status_code == 401

    # Attempt to download without auth
    res_down = unauth_client.get("/api/files/some-id")
    assert res_down.status_code == 401

    # Attempt to delete without auth
    res_del = unauth_client.delete("/api/files/some-id")
    assert res_del.status_code == 401


def test_protected_route_with_header_token():
    token = get_or_create_auth_token()
    headers = {"X-PocketDrop-Token": token}
    res = client.get("/api/files", headers=headers)
    assert res.status_code == 200
    assert "files" in res.json()


def test_csrf_protection_on_state_changing_requests():
    token = get_or_create_auth_token()
    session_client = TestClient(app)

    # Pair to get cookie and CSRF
    pair_res = session_client.post("/api/auth/pair", json={"pin": token})
    assert pair_res.status_code == 200
    csrf_token = pair_res.json()["csrf_token"]

    # State-changing request without CSRF header must fail with 403
    upload_res_no_csrf = session_client.post(
        "/api/uploads",
        files={"files": ("test.txt", b"hello", "text/plain")}
    )
    assert upload_res_no_csrf.status_code == 403

    # State-changing request with wrong CSRF header must fail with 403
    upload_res_bad_csrf = session_client.post(
        "/api/uploads",
        files={"files": ("test.txt", b"hello", "text/plain")},
        headers={"X-CSRF-Token": "invalid_csrf_token"}
    )
    assert upload_res_bad_csrf.status_code == 403

    # State-changing request with valid CSRF header succeeds
    upload_res_ok = session_client.post(
        "/api/uploads",
        files={"files": ("test.txt", b"hello", "text/plain")},
        headers={"X-CSRF-Token": csrf_token}
    )
    assert upload_res_ok.status_code == 200
