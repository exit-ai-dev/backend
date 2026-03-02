"""OpenAI text-embedding-3-small wrapper."""
from __future__ import annotations
from typing import List

import httpx
from app.config import settings

EMBED_MODEL = "text-embedding-3-small"
BATCH_SIZE = 100


async def get_embeddings(texts: List[str]) -> List[List[float]]:
    """Return embeddings for a list of texts (batched)."""
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    results: List[List[float]] = []
    async with httpx.AsyncClient(timeout=60.0) as client:
        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i : i + BATCH_SIZE]
            resp = await client.post(
                f"{settings.openai_base_url}/embeddings",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json={"model": EMBED_MODEL, "input": batch},
            )
            resp.raise_for_status()
            data = resp.json()
            results.extend(item["embedding"] for item in data["data"])
    return results
