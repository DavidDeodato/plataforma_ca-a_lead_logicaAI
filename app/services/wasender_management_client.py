from __future__ import annotations

from typing import Any

import httpx

from app.core.config import get_settings


class WasenderManagementClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.timeout = httpx.Timeout(20.0, connect=5.0)

    def _headers(self) -> dict[str, str]:
        if not self.settings.has_wasender_management_credentials:
            raise RuntimeError("WASENDER_PERSONAL_ACCESS_TOKEN ainda não configurado.")
        return {
            "Authorization": f"Bearer {self.settings.wasender_personal_access_token}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.settings.wasender_api_base_url.rstrip('/')}{path}"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.request(method=method, url=url, headers=self._headers(), json=json)
        except httpx.TimeoutException as exc:
            raise RuntimeError(f"WASender demorou demais para responder: {exc}") from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Falha de transporte ao falar com o WASender: {exc}") from exc

        if response.is_error:
            try:
                payload = response.json()
                detail = payload.get("error") or payload.get("message") or response.text
            except ValueError:
                detail = response.text
            raise RuntimeError(f"WASender respondeu {response.status_code}: {detail}")

        payload = response.json()
        if isinstance(payload, dict) and payload.get("success") is False:
            detail = payload.get("error") or payload.get("message") or "Operação recusada pelo WASender."
            raise RuntimeError(str(detail))
        return payload

    def list_sessions(self) -> list[dict[str, Any]]:
        payload = self._request("GET", "/api/whatsapp-sessions")
        data = payload.get("data")
        return [item for item in data if isinstance(item, dict)] if isinstance(data, list) else []

    def get_session_details(self, wasender_session_id: int) -> dict[str, Any]:
        payload = self._request("GET", f"/api/whatsapp-sessions/{wasender_session_id}")
        data = payload.get("data")
        return data if isinstance(data, dict) else {}

    def create_session(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._request("POST", "/api/whatsapp-sessions", json=payload)
        data = response.get("data")
        return data if isinstance(data, dict) else {}

    def connect_session(self, wasender_session_id: int) -> dict[str, Any]:
        payload = self._request("POST", f"/api/whatsapp-sessions/{wasender_session_id}/connect")
        data = payload.get("data")
        return data if isinstance(data, dict) else {}

    def get_session_qrcode(self, wasender_session_id: int) -> str | None:
        payload = self._request("GET", f"/api/whatsapp-sessions/{wasender_session_id}/qrcode")
        data = payload.get("data")
        if not isinstance(data, dict):
            return None
        qr_code = data.get("qrCode")
        return str(qr_code) if qr_code else None
