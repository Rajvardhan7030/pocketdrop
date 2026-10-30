"""Security and authentication management for PocketDrop."""

import hmac
import logging
import os
import secrets
import time
from typing import Dict, Optional, Tuple
from fastapi import HTTPException, Request, Response, status
from app.config import settings

logger = logging.getLogger("pocketdrop.security")

# Session store structure: session_id -> {"csrf_token": str, "created_at": float}
_sessions: Dict[str, Dict[str, float]] = {}
SESSION_TTL_SECONDS = 86400 * 7  # 7 days

# Cached or active auth pairing token
_active_auth_token: Optional[str] = None


def normalize_pin(val: Optional[str]) -> str:
    """
    Normalize PIN or token for tolerant matching.
    Strips leading/trailing whitespace, and strips internal spaces/hyphens for numeric PINs.
    """
    if not val:
        return ""
    cleaned = val.strip()
    digits_only = cleaned.replace(" ", "").replace("-", "")
    if digits_only.isdigit():
        return digits_only
    return cleaned


def get_or_create_auth_token(force_new: bool = False, custom_token: Optional[str] = None) -> str:
    """
    Retrieve or generate the master pairing token.
    Uses custom_token or POCKETDROP_AUTH_TOKEN if configured; otherwise generates a secure 6-digit PIN.
    If force_new is True, generates a fresh PIN and overwrites existing token.
    """
    global _active_auth_token
    if custom_token:
        _active_auth_token = custom_token.strip()
        return _active_auth_token

    if settings.AUTH_TOKEN and not force_new:
        return settings.AUTH_TOKEN

    if not force_new and _active_auth_token is not None:
        return _active_auth_token

    # Check if previously saved in data directory
    token_file = settings.DATA_DIR / ".auth_token"
    if not force_new and token_file.exists():
        try:
            token = token_file.read_text(encoding="utf-8").strip()
            if token:
                _active_auth_token = token
                return _active_auth_token
        except Exception:
            pass

    # Generate a user-friendly 6-digit numeric pairing PIN
    generated_pin = f"{secrets.randbelow(900000) + 100000}"
    try:
        settings.ensure_directories()
        # Restrict permissions on the token file to user only (0600)
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        mode = 0o600
        fd = os.open(str(token_file), flags, mode)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(generated_pin)
    except Exception as e:
        logger.warning("Could not persist auth token file: %s", e)

    _active_auth_token = generated_pin
    return _active_auth_token


def create_session() -> Tuple[str, str]:
    """Create a new session, returning (session_id, csrf_token)."""
    session_id = secrets.token_hex(24)
    csrf_token = secrets.token_hex(24)
    _sessions[session_id] = {
        "csrf_token": csrf_token,
        "created_at": time.time()
    }
    return session_id, csrf_token


def validate_session(session_id: str) -> Optional[str]:
    """Return csrf_token if session_id is valid and unexpired; otherwise None."""
    session_data = _sessions.get(session_id)
    if not session_data:
        return None

    # Check TTL
    if time.time() - session_data["created_at"] > SESSION_TTL_SECONDS:
        _sessions.pop(session_id, None)
        return None

    return session_data["csrf_token"]


def revoke_session(session_id: str) -> None:
    """Invalidate a session."""
    _sessions.pop(session_id, None)


def verify_pairing_token(candidate: str) -> bool:
    """Constant-time comparison against master pairing token with space/hyphen normalization."""
    master = get_or_create_auth_token()
    clean_candidate = normalize_pin(candidate)
    clean_master = normalize_pin(master)
    if not clean_candidate or not clean_master:
        return False
    return secrets.compare_digest(clean_candidate, clean_master)


async def require_auth(request: Request) -> None:
    """
    FastAPI dependency enforcing authentication on protected routes.
    Accepts:
    1. X-PocketDrop-Token header matching master pairing token.
    2. Authorization: Bearer <token> matching master pairing token.
    3. Valid pocketdrop_session cookie (with CSRF verification on state-changing requests).
    """
    # 1. Direct header token (for API clients, curl, testing)
    header_token = request.headers.get("X-PocketDrop-Token")
    if header_token and verify_pairing_token(header_token):
        return

    # 2. Bearer token
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        bearer_token = auth_header[7:].strip()
        if verify_pairing_token(bearer_token):
            return

    # 3. Cookie session
    session_id = request.cookies.get("pocketdrop_session")
    if session_id:
        expected_csrf = validate_session(session_id)
        if expected_csrf:
            # If state-changing request (POST, PUT, DELETE, PATCH), verify CSRF
            if request.method in ("POST", "PUT", "DELETE", "PATCH"):
                client_csrf = request.headers.get("X-CSRF-Token")
                if not client_csrf or not secrets.compare_digest(client_csrf, expected_csrf):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="CSRF token validation failed."
                    )
            return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Please pair your device."
    )
