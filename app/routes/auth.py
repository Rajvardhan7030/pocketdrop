"""Authentication and pairing API routes."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from app.security import (
    create_session,
    revoke_session,
    validate_session,
    verify_pairing_token,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class PairRequest(BaseModel):
    pin: Optional[str] = Field(None, description="Pairing PIN or master token")
    token: Optional[str] = Field(None, description="Pairing PIN or master token")


@router.post("/pair", summary="Pair a device with the server")
async def pair_device(req: PairRequest, response: Response):
    """
    Verify the pairing PIN/token entered by the user.
    On success, creates a secure session and returns a CSRF token.
    """
    candidate = (req.pin or req.token or "").strip()
    if not candidate or not verify_pairing_token(candidate):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid pairing PIN or token."
        )

    session_id, csrf_token = create_session()

    # Set secure HttpOnly session cookie
    response.set_cookie(
        key="pocketdrop_session",
        value=session_id,
        httponly=True,
        samesite="lax",
        path="/"
    )

    return {
        "status": "ok",
        "csrf_token": csrf_token
    }


@router.get("/check", summary="Check current pairing/session status")
async def check_auth_status(request: Request):
    """Check if the requesting client has an active authenticated session."""
    session_id = request.cookies.get("pocketdrop_session")
    if session_id:
        csrf_token = validate_session(session_id)
        if csrf_token:
            return {"authenticated": True, "csrf_token": csrf_token}

    # Also check direct header token
    header_token = request.headers.get("X-PocketDrop-Token")
    if header_token and verify_pairing_token(header_token):
        return {"authenticated": True, "csrf_token": None}

    return {"authenticated": False}


@router.post("/logout", summary="End the current session")
async def logout(request: Request, response: Response):
    """Invalidate current session cookie."""
    session_id = request.cookies.get("pocketdrop_session")
    if session_id:
        revoke_session(session_id)
    response.delete_cookie(key="pocketdrop_session", path="/")
    return {"status": "ok"}
