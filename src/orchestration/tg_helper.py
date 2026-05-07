"""
tg_helper.py - Telegram Bot API Wrapper (dùng urllib thuần, không cần requests)
================================================================================
"""

import json
import urllib.request
import urllib.parse
import urllib.error
from typing import Optional

import sys
import ssl

class TelegramBot:
    BASE = "https://api.telegram.org/bot{token}/{method}"

    def __init__(self, token: str):
        self.token = token
        # Bỏ qua xác thực SSL (Fix lỗi tự ký SSL certificate của Windows/Antivirus)
        self.ssl_ctx = ssl.create_default_context()
        self.ssl_ctx.check_hostname = False
        self.ssl_ctx.verify_mode = ssl.CERT_NONE

    def _call(self, method: str, payload: dict = None, timeout: int = 10) -> Optional[dict]:
        url = self.BASE.format(token=self.token, method=method)
        try:
            data = json.dumps(payload or {}, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(
                url, data=data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=timeout, context=self.ssl_ctx) as resp:
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

    def send_photo(self, chat_id: int, photo_path: str, caption: str = "", parse_mode: str = "HTML") -> bool:
        """Gửi hình ảnh kèm tiêu đề."""
        import os
        import uuid
        boundary = uuid.uuid4().hex
        
        try:
            with open(photo_path, "rb") as f:
                photo_data = f.read()
            filename = os.path.basename(photo_path)
            
            body = bytearray()
            body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{chat_id}\r\n".encode('utf-8')
            if caption:
                body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"caption\"\r\n\r\n{caption}\r\n".encode('utf-8')
                body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"parse_mode\"\r\n\r\n{parse_mode}\r\n".encode('utf-8')
                
            body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"photo\"; filename=\"{filename}\"\r\nContent-Type: image/png\r\n\r\n".encode('utf-8')
            body += photo_data + b"\r\n"
            body += f"--{boundary}--\r\n".encode('utf-8')
            
            url = self.BASE.format(token=self.token, method="sendPhoto")
            req = urllib.request.Request(url, data=body, method="POST")
            req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
            with urllib.request.urlopen(req, timeout=30, context=self.ssl_ctx) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                return res.get("ok", False)
        except Exception as e:
            print(f"[TG] Lỗi send_photo: {e}")
            return False

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
