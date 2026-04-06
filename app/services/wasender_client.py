from __future__ import annotations

from typing import Any

import httpx

from app.core.config import get_settings


class WasenderClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.timeout = httpx.Timeout(12.0, connect=5.0)

    def _headers(self) -> dict[str, str]:
        if not self.settings.has_wasender_credentials:
            raise RuntimeError("WASENDER_API_KEY ainda não configurada.")
        return {
            "Authorization": f"Bearer {self.settings.wasender_api_key}",
            "Content-Type": "application/json",
        }

    def send_text_message(self, to: str, text: str) -> dict[str, Any]:
        payload = {"to": to, "text": text}
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.settings.wasender_api_base_url.rstrip('/')}/api/send-message",
                    headers=self._headers(),
                    json=payload,
                )
                if response.is_error:
                    return {
                        "data": {"status": "send_failed", "msgId": None},
                        "error": {
                            "type": "http_error",
                            "status_code": response.status_code,
                            "body": response.text,
                        },
                    }
                return response.json()
        except httpx.TimeoutException as exc:
            return {
                "data": {"status": "send_timeout", "msgId": None},
                "error": {"type": "timeout", "message": str(exc)},
            }
        except httpx.HTTPError as exc:
            return {
                "data": {"status": "send_failed", "msgId": None},
                "error": {"type": "transport_error", "message": str(exc)},
            }
