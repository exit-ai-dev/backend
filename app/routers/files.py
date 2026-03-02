"""
File upload / indexing / listing endpoints.

POST   /api/files/upload       — upload & index a file
GET    /api/files/list         — list indexed files
DELETE /api/files/{file_id}    — remove file from index + storage
POST   /api/files/{file_id}/reindex  — re-index an already-stored file
"""
from __future__ import annotations
import uuid
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File

from app.services.file_provider import get_file_provider
from app.services.rag import index_file
from app.services.vector_store import get_vector_store
from app.services.document_extractor import SUPPORTED

router = APIRouter(prefix="/api/files", tags=["files"])
logger = logging.getLogger(__name__)


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in SUPPORTED:
        raise HTTPException(
            400,
            f"対応していないファイル形式です: {suffix}。"
            f"対応形式: {', '.join(sorted(SUPPORTED))}",
        )

    content = await file.read()
    if not content:
        raise HTTPException(400, "ファイルが空です")

    file_id = str(uuid.uuid4())

    # 1. persist raw file
    provider = get_file_provider()
    await provider.save(file_id, file.filename or file_id, content)

    # 2. extract + embed + store
    try:
        chunk_count = await index_file(file_id, file.filename or file_id, content)
    except Exception as exc:
        logger.error("[files] indexing failed for %s: %s", file.filename, exc)
        # roll back stored file
        try:
            await provider.delete(file_id)
        except Exception:
            pass
        raise HTTPException(500, f"インデックス化に失敗しました: {exc}")

    return {
        "file_id": file_id,
        "filename": file.filename,
        "chunk_count": chunk_count,
        "status": "indexed",
    }


@router.get("/list")
async def list_files():
    return {"files": get_vector_store().list_files()}


@router.delete("/{file_id}")
async def delete_file(file_id: str):
    get_vector_store().delete(file_id)
    try:
        await get_file_provider().delete(file_id)
    except FileNotFoundError:
        pass
    return {"status": "deleted", "file_id": file_id}


@router.post("/{file_id}/reindex")
async def reindex_file(file_id: str):
    """Re-embed an already-stored file (e.g. after model change)."""
    try:
        content = await get_file_provider().load(file_id)
    except FileNotFoundError:
        raise HTTPException(404, "ファイルが見つかりません")

    # filename is stored in vector store
    files = {f["file_id"]: f["filename"] for f in get_vector_store().list_files()}
    filename = files.get(file_id, file_id)

    try:
        chunk_count = await index_file(file_id, filename, content)
    except Exception as exc:
        raise HTTPException(500, f"再インデックス化に失敗しました: {exc}")

    return {"file_id": file_id, "filename": filename, "chunk_count": chunk_count, "status": "reindexed"}
