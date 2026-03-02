from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List
import logging

from app.services.openai_service import complete_once, stream_completion

router = APIRouter(prefix="/api", tags=["chat"])
logger = logging.getLogger(__name__)


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]
    temperature: float = 0.3
    max_tokens: int = 512


async def _inject_rag(messages: List[dict]) -> List[dict]:
    """
    Query RAG with the latest user message and prepend relevant chunks
    to the system prompt.  If RAG is unavailable or empty, returns messages unchanged.
    """
    try:
        from app.services.rag import query_rag, build_rag_context
        last_user = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"),
            None,
        )
        if not last_user:
            return messages

        results = await query_rag(last_user)
        context = build_rag_context(results)
        if not context:
            return messages

        # Prepend context to existing system message, or insert a new one
        msgs = list(messages)
        if msgs and msgs[0]["role"] == "system":
            msgs[0] = {**msgs[0], "content": context + msgs[0]["content"]}
        else:
            msgs.insert(0, {"role": "system", "content": context})
        return msgs

    except Exception as exc:
        logger.warning("[RAG] skipped — %s", exc)
        return messages


@router.post("/chat")
async def chat(req: ChatRequest):
    messages = await _inject_rag([m.dict() for m in req.messages])
    try:
        result = await complete_once(messages, req.temperature, req.max_tokens)
        return result
    except RuntimeError as e:
        if "API key" in str(e):
            raise HTTPException(status_code=401, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upstream error: {str(e)}")


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    messages = await _inject_rag([m.dict() for m in req.messages])

    async def gen():
        try:
            async for chunk in stream_completion(messages, req.temperature, req.max_tokens):
                yield chunk
        except RuntimeError as e:
            yield f"ERROR: {str(e)}"
        except Exception as e:
            yield f"ERROR: Upstream error: {str(e)}"

    return StreamingResponse(gen(), media_type="text/plain; charset=utf-8")
