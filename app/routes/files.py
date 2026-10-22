"""API routes for file uploads, listings, downloads, and deletion."""

import urllib.parse
from typing import List
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.security import require_auth
from app.storage import (
    StorageNotFoundError,
    StoragePathEscapeError,
    StorageQuotaError,
    StorageService,
)

router = APIRouter(prefix="/api", tags=["files"])


def get_storage_service() -> StorageService:
    """Dependency that supplies the configured StorageService instance."""
    return StorageService()


@router.post("/uploads", summary="Upload one or more files")
async def upload_files(
    files: List[UploadFile] = File(...),
    _: None = Depends(require_auth),
    storage_service: StorageService = Depends(get_storage_service)
):
    """
    Authorized endpoint to upload one or more files.
    Streams files directly to disk and enforces quotas atomically.
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided for upload."
        )

    saved_items = []
    try:
        for file in files:
            info = await storage_service.save_upload(file)
            saved_items.append({
                "id": info.id,
                "filename": info.filename,
                "size_bytes": info.size_bytes,
                "media_type": info.media_type,
                "sha256": info.sha256,
                "created_at": info.created_at
            })
    except StorageQuotaError as e:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload processing failed: {str(e)}"
        )

    return {"uploaded": saved_items}


@router.get("/files", summary="List authorized shared files")
async def list_files(
    _: None = Depends(require_auth),
    storage_service: StorageService = Depends(get_storage_service)
):
    """Return metadata of all shared files. Opaque internal IDs are exposed, not paths."""
    files = storage_service.list_files()
    return {
        "files": [
            {
                "id": f.id,
                "filename": f.filename,
                "size_bytes": f.size_bytes,
                "media_type": f.media_type,
                "sha256": f.sha256,
                "created_at": f.created_at
            }
            for f in files
        ]
    }


@router.get("/files/{file_id}", summary="Download a shared file")
async def download_file(
    file_id: str,
    _: None = Depends(require_auth),
    storage_service: StorageService = Depends(get_storage_service)
):
    """
    Download a file by its internal ID.
    Enforces safe attachment headers and strict path validation.
    """
    try:
        file_path, info = storage_service.get_file_disk_path(file_id)
    except StorageNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested file was not found."
        )
    except StoragePathEscapeError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid file identifier."
        )

    # Encode filename for Content-Disposition header
    encoded_filename = urllib.parse.quote(info.filename)
    headers = {
        "Content-Disposition": f"attachment; filename=\"{info.filename}\"; filename*=UTF-8''{encoded_filename}",
        "X-Content-Type-Options": "nosniff"
    }

    # Serve as binary attachment stream
    return FileResponse(
        path=file_path,
        media_type="application/octet-stream",
        headers=headers
    )


@router.delete("/files/{file_id}", summary="Delete a shared file")
async def delete_file(
    file_id: str,
    _: None = Depends(require_auth),
    storage_service: StorageService = Depends(get_storage_service)
):
    """Delete a shared file after authorization."""
    try:
        storage_service.delete_file(file_id)
    except StorageNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested file was not found."
        )

    return {"status": "deleted", "id": file_id}
