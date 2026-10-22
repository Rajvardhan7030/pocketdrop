"""API routes for text inbox and snippet transfers."""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.config import settings
from app.db import get_db
from app.security import require_auth

router = APIRouter(prefix="/api/text", tags=["text"])


class TextSnippetCreate(BaseModel):
    content: str = Field(..., min_length=1, description="Text snippet content")


class TextSnippetResponse(BaseModel):
    id: str
    content: str
    created_at: str


@router.post("", response_model=TextSnippetResponse, summary="Submit a text snippet")
async def create_text_snippet(
    snippet: TextSnippetCreate,
    _: None = Depends(require_auth)
):
    """
    Save a plain-text snippet to SQLite.
    Enforces maximum character length limit and parameterized insertion.
    """
    raw_content = snippet.content
    if len(raw_content) > settings.MAX_TEXT_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"Text snippet exceeds maximum allowed length of {settings.MAX_TEXT_LENGTH} characters."
        )

    if not raw_content.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Text snippet cannot be empty or purely whitespace."
        )

    text_id = str(uuid.uuid4())

    with get_db() as conn:
        conn.execute(
            "INSERT INTO text_messages (id, content) VALUES (?, ?)",
            (text_id, raw_content)
        )
        # Prune older messages beyond retention limit (keep newest 200)
        conn.execute("""
            DELETE FROM text_messages
            WHERE id NOT IN (
                SELECT id FROM text_messages ORDER BY created_at DESC LIMIT 200
            )
        """)
        cursor = conn.execute("SELECT created_at FROM text_messages WHERE id = ?", (text_id,))
        row = cursor.fetchone()
        created_at = str(row["created_at"])

    return TextSnippetResponse(
        id=text_id,
        content=raw_content,
        created_at=created_at
    )


@router.get("", summary="Retrieve text history")
async def list_text_snippets(
    limit: int = Query(50, ge=1, le=100, description="Number of recent snippets to retrieve"),
    _: None = Depends(require_auth)
):
    """Retrieve recent plain-text snippets ordered by creation time descending."""
    with get_db() as conn:
        cursor = conn.execute(
            """
            SELECT id, content, created_at
            FROM text_messages
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,)
        )
        rows = cursor.fetchall()
        snippets = [
            {
                "id": row["id"],
                "content": row["content"],
                "created_at": str(row["created_at"])
            }
            for row in rows
        ]

    return {"messages": snippets}


@router.delete("/{text_id}", summary="Delete a text snippet")
async def delete_text_snippet(
    text_id: str,
    _: None = Depends(require_auth)
):
    """Delete a specific text snippet by ID."""
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM text_messages WHERE id = ?", (text_id,))
        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Text snippet not found."
            )

    return {"status": "deleted", "id": text_id}
