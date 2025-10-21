# app/routers/line.py
"""
LINE Messaging API Webhook
"""
import os
import hmac
import hashlib
import base64
import json
from fastapi import APIRouter, Request, HTTPException, Header
from typing import Optional
from app.services.line_service import LineService
from app.services.openai_service import complete_once
from app.database import save_line_message, get_line_conversation

router = APIRouter(prefix="/api/line", tags=["line"])

LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")


def verify_signature(body: bytes, signature: str) -> bool:
    """
    LINE Platform からのリクエストを検証
    """
    if not LINE_CHANNEL_SECRET or not signature:
        # Channel Secretが未設定または署名がない場合はスキップ
        print("[LINE Webhook] Signature verification skipped")
        return True

    hash_digest = hmac.new(
        LINE_CHANNEL_SECRET.encode('utf-8'),
        body,
        hashlib.sha256
    ).digest()
    # LINEはbase64エンコードされた署名を送信
    expected_signature = base64.b64encode(hash_digest).decode('utf-8')

    is_valid = hmac.compare_digest(signature, expected_signature)
    if not is_valid:
        print(f"[LINE Webhook] Signature mismatch. Expected: {expected_signature[:20]}..., Got: {signature[:20]}...")
    return is_valid


@router.post("/webhook")
async def line_webhook(
    request: Request,
    x_line_signature: Optional[str] = Header(None)
):
    """
    LINE Webhookエンドポイント
    ユーザーからのメッセージを受信し、OpenAI APIで応答を生成してLINEに返信
    """
    body = await request.body()

    # 署名検証
    if x_line_signature and not verify_signature(body, x_line_signature):
        raise HTTPException(status_code=400, detail="Invalid signature")

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # イベント処理
    for event in data.get("events", []):
        await handle_line_event(event)

    return {"status": "ok"}


async def handle_line_event(event: dict):
    """
    LINEイベントを処理
    """
    event_type = event.get("type")

    if event_type != "message":
        return

    message_type = event.get("message", {}).get("type")
    if message_type != "text":
        return

    # ユーザー情報
    user_id = event.get("source", {}).get("userId")
    reply_token = event.get("replyToken")
    user_message = event.get("message", {}).get("text", "")

    if not user_id or not reply_token or not user_message:
        return

    try:
        # LINEサービスを初期化
        line_service = LineService(LINE_CHANNEL_ACCESS_TOKEN)

        # 会話履歴を取得（データベースから）
        conversation_history = await get_user_conversation(user_id)

        # システムプロンプト
        system_prompt = "あなたは親切なAIアシスタントです。ユーザーの質問に簡潔かつ丁寧に答えてください。"

        # メッセージリストを構築
        messages = [
            {"role": "system", "content": system_prompt},
            *conversation_history,
            {"role": "user", "content": user_message}
        ]

        # OpenAI APIで応答を生成
        result = await complete_once(messages, temperature=0.7, max_tokens=500)
        ai_response = result.get("content", "申し訳ございません。応答を生成できませんでした。")

        # 会話履歴を保存
        await save_user_message(user_id, user_message, ai_response)

        # LINEに返信
        await line_service.reply_message(reply_token, ai_response)

    except Exception as e:
        print(f"[LINE Webhook] Error: {e}")
        # エラー時はユーザーにエラーメッセージを返信
        try:
            line_service = LineService(LINE_CHANNEL_ACCESS_TOKEN)
            await line_service.reply_message(
                reply_token,
                "申し訳ございません。エラーが発生しました。しばらくしてからもう一度お試しください。"
            )
        except:
            pass


async def get_user_conversation(user_id: str) -> list:
    """
    ユーザーの会話履歴を取得（最新10件）
    """
    conversation_history = get_line_conversation(user_id, limit=10)
    print(f"[LINE] Loaded {len(conversation_history)} messages for user {user_id}")
    return conversation_history


async def save_user_message(user_id: str, user_message: str, ai_response: str):
    """
    会話履歴をデータベースに保存
    """
    # ユーザーメッセージを保存
    save_line_message(user_id, "user", user_message)
    # AIの応答を保存
    save_line_message(user_id, "assistant", ai_response)
    print(f"[LINE] Saved conversation for user {user_id}")


@router.get("/health")
async def line_health():
    """
    LINE連携のヘルスチェック
    """
    return {
        "status": "ok",
        "channel_secret_configured": bool(LINE_CHANNEL_SECRET),
        "access_token_configured": bool(LINE_CHANNEL_ACCESS_TOKEN)
    }
