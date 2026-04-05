"""
tg_helper.py - Telegram Bot API Wrapper (dùng urllib thuần, không cần requests)
================================================================================
"""

import json
import urllib.request
import urllib.parse
import urllib.error
from typing import Optional


class TelegramBot:
    BASE = "https://api.telegram.org/bot{token}/{method}"

    def __init__(self, token: str):
        self.token = token

    def _call(self, method: str, payload: dict = None, timeout: int = 10) -> Optional[dict]:
        url = self.BASE.format(token=self.token, method=method)
        try:
            data = json.dumps(payload or {}).encode("utf-8")
            req = urllib.request.Request(
                url, data=data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            print(f"[TG] HTTP {e.code}: {body[:200]}")
            return None
        except Exception as e:
            print(f"[TG] Lỗi gọi API {method}: {e}")
            return None

    def send_message(self, chat_id: int, text: str, parse_mode: str = "HTML") -> bool:
        """Gửi tin nhắn text."""
        result = self._call("sendMessage", {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        })
        return result is not None and result.get("ok", False)

    def get_updates(self, offset: int = 0, timeout: int = 30) -> list[dict]:
        """Long-poll lấy tin nhắn mới. timeout=30 → block tối đa 30s."""
        result = self._call("getUpdates", {
            "offset": offset,
            "timeout": timeout,
            "allowed_updates": ["message"]
        }, timeout=timeout + 5)
        if result and result.get("ok"):
            return result.get("result", [])
        return []

    def delete_webhook(self):
        """Xóa webhook nếu có (bắt buộc trước khi dùng getUpdates)."""
        self._call("deleteWebhook", {})
