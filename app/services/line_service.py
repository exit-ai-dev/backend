# app/services/line_service.py
"""
LINE Messaging API サービス
"""
import httpx
from typing import List, Dict, Any, Optional


class LineService:
    """LINE Messaging API クライアント"""

    def __init__(self, channel_access_token: str):
        self.channel_access_token = channel_access_token
        self.api_base = "https://api.line.me/v2/bot"

    def _headers(self) -> Dict[str, str]:
        """認証ヘッダー"""
        return {
            "Authorization": f"Bearer {self.channel_access_token}",
            "Content-Type": "application/json"
        }

    async def reply_message(self, reply_token: str, text: str):
        """
        返信メッセージを送信
        """
        url = f"{self.api_base}/message/reply"
        payload = {
            "replyToken": reply_token,
            "messages": [
                {
                    "type": "text",
                    "text": text
                }
            ]
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=self._headers(), json=payload)
            response.raise_for_status()
            return response.json()

    async def push_message(self, user_id: str, text: str):
        """
        プッシュメッセージを送信
        """
        url = f"{self.api_base}/message/push"
        payload = {
            "to": user_id,
            "messages": [
                {
                    "type": "text",
                    "text": text
                }
            ]
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=self._headers(), json=payload)
            response.raise_for_status()
            return response.json()

    async def push_flex_message(
        self,
        user_id: str,
        alt_text: str,
        flex_content: Dict[str, Any]
    ):
        """
        Flexメッセージを送信（リッチなUI）
        """
        url = f"{self.api_base}/message/push"
        payload = {
            "to": user_id,
            "messages": [
                {
                    "type": "flex",
                    "altText": alt_text,
                    "contents": flex_content
                }
            ]
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=self._headers(), json=payload)
            response.raise_for_status()
            return response.json()

    async def get_profile(self, user_id: str) -> Dict[str, Any]:
        """
        ユーザープロフィールを取得
        """
        url = f"{self.api_base}/profile/{user_id}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self._headers())
            response.raise_for_status()
            return response.json()

    async def send_rich_menu_button(
        self,
        reply_token: str,
        text: str,
        button_text: str,
        liff_url: str
    ):
        """
        LIFFアプリへのボタンを含むメッセージを送信
        """
        url = f"{self.api_base}/message/reply"
        payload = {
            "replyToken": reply_token,
            "messages": [
                {
                    "type": "template",
                    "altText": text,
                    "template": {
                        "type": "buttons",
                        "text": text,
                        "actions": [
                            {
                                "type": "uri",
                                "label": button_text,
                                "uri": liff_url
                            }
                        ]
                    }
                }
            ]
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=self._headers(), json=payload)
            response.raise_for_status()
            return response.json()
