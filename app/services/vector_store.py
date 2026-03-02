"""
Lightweight vector store backed by SQLite + numpy cosine similarity.
No external services required.
"""
from __future__ import annotations
import sqlite3
from dataclasses import dataclass
from typing import List

import numpy as np

from app.config import settings


@dataclass
class SearchResult:
    file_id: str
    filename: str
    chunk_index: int
    text: str
    score: float


class VectorStore:
    def __init__(self, db_path: str | None = None) -> None:
        self._db = db_path or settings.rag_db_path
        self._init()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db)

    def _init(self) -> None:
        with self._connect() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id      TEXT    NOT NULL,
                    filename     TEXT    NOT NULL,
                    chunk_index  INTEGER NOT NULL,
                    text         TEXT    NOT NULL,
                    embedding    BLOB    NOT NULL,
                    indexed_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            c.execute("CREATE INDEX IF NOT EXISTS idx_file ON chunks(file_id)")

    # ── write ──────────────────────────────────────────────────────────────────

    def upsert(
        self,
        file_id: str,
        filename: str,
        chunks: List[str],
        embeddings: List[List[float]],
    ) -> None:
        with self._connect() as c:
            c.execute("DELETE FROM chunks WHERE file_id = ?", (file_id,))
            c.executemany(
                "INSERT INTO chunks (file_id, filename, chunk_index, text, embedding) VALUES (?,?,?,?,?)",
                [
                    (file_id, filename, i, text, _to_blob(emb))
                    for i, (text, emb) in enumerate(zip(chunks, embeddings))
                ],
            )

    def delete(self, file_id: str) -> None:
        with self._connect() as c:
            c.execute("DELETE FROM chunks WHERE file_id = ?", (file_id,))

    # ── read ───────────────────────────────────────────────────────────────────

    def list_files(self) -> List[dict]:
        with self._connect() as c:
            rows = c.execute("""
                SELECT file_id, filename,
                       COUNT(*)     AS chunk_count,
                       MAX(indexed_at) AS indexed_at
                FROM   chunks
                GROUP  BY file_id
                ORDER  BY indexed_at DESC
            """).fetchall()
        return [
            {"file_id": r[0], "filename": r[1], "chunk_count": r[2], "indexed_at": r[3]}
            for r in rows
        ]

    def search(self, query_embedding: List[float], top_k: int = 5) -> List[SearchResult]:
        q = _normalise(np.array(query_embedding, dtype=np.float32))
        with self._connect() as c:
            rows = c.execute(
                "SELECT file_id, filename, chunk_index, text, embedding FROM chunks"
            ).fetchall()
        if not rows:
            return []
        results: List[SearchResult] = []
        for file_id, filename, chunk_idx, text, blob in rows:
            vec = _normalise(np.frombuffer(blob, dtype=np.float32))
            score = float(np.dot(q, vec))
            results.append(SearchResult(file_id, filename, chunk_idx, text, score))
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]


# ── helpers ───────────────────────────────────────────────────────────────────

def _to_blob(embedding: List[float]) -> bytes:
    return np.array(embedding, dtype=np.float32).tobytes()

def _normalise(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    return v / (n + 1e-10)


# ── singleton ─────────────────────────────────────────────────────────────────

_store: VectorStore | None = None

def get_vector_store() -> VectorStore:
    global _store
    if _store is None:
        _store = VectorStore()
    return _store
