"""RAG pipeline: index files → query relevant chunks → build context."""
from __future__ import annotations
import logging
from typing import List

from app.config import settings
from app.services.document_extractor import extract_text, chunk_text
from app.services.embeddings import get_embeddings
from app.services.vector_store import SearchResult, get_vector_store

logger = logging.getLogger(__name__)


async def index_file(file_id: str, filename: str, content: bytes) -> int:
    """Extract → chunk → embed → store.  Returns number of chunks stored."""
    text = extract_text(filename, content)
    if not text.strip():
        raise ValueError(f"No text could be extracted from {filename!r}")

    chunks = chunk_text(
        text,
        chunk_size=settings.rag_chunk_size,
        overlap=settings.rag_chunk_overlap,
    )
    logger.info("[RAG] %s → %d chunks", filename, len(chunks))

    embeddings = await get_embeddings(chunks)

    store = get_vector_store()
    store.upsert(file_id, filename, chunks, embeddings)
    return len(chunks)


async def query_rag(question: str) -> List[SearchResult]:
    """Return top-k relevant chunks for *question*, filtered by score threshold."""
    store = get_vector_store()
    if not store.list_files():
        return []

    q_emb = await get_embeddings([question])
    results = store.search(q_emb[0], top_k=settings.rag_top_k)
    return [r for r in results if r.score >= settings.rag_score_threshold]


def build_rag_context(results: List[SearchResult]) -> str:
    """Format retrieved chunks as a system-prompt prefix."""
    if not results:
        return ""
    lines = ["## 参照ドキュメント（ファイルサーバーより自動取得）\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"### [{i}] {r.filename}  (chunk {r.chunk_index + 1})")
        lines.append(r.text.strip())
        lines.append("")
    lines.append("---")
    lines.append("上記ドキュメントを根拠に回答してください。関係ない場合は無視してください。\n")
    return "\n".join(lines)
