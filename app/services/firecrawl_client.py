from __future__ import annotations

import time
from typing import Any

import httpx

from app.core.config import get_settings


class FirecrawlClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.timeout = httpx.Timeout(60.0, connect=20.0)

    def _headers(self) -> dict[str, str]:
        if not self.settings.has_firecrawl_credentials:
            raise RuntimeError("FIRECRAWL_API_KEY não configurada.")
        return {
            "Authorization": f"Bearer {self.settings.firecrawl_api_key}",
            "Content-Type": "application/json",
        }

    def search(self, query: str, limit: int = 5, location: str | None = None) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {
            "query": query,
            "limit": limit,
            "ignoreInvalidURLs": True,
            "timeout": 60000,
            "scrapeOptions": {
                "formats": ["markdown"],
                "onlyMainContent": True,
            },
        }
        if location:
            payload["location"] = location

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                "https://api.firecrawl.dev/v1/search",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])

    def extract(
        self,
        urls: list[str],
        *,
        prompt: str | None = None,
        schema: dict[str, Any] | None = None,
        enable_web_search: bool = False,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "urls": urls,
            "ignoreInvalidURLs": True,
            "showSources": True,
            "enableWebSearch": enable_web_search,
            "scrapeOptions": {
                "formats": ["markdown"],
                "onlyMainContent": True,
            },
        }
        if prompt:
            payload["prompt"] = prompt
        if schema:
            payload["schema"] = schema

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                "https://api.firecrawl.dev/v2/extract",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    def start_agent(
        self,
        *,
        prompt: str,
        urls: list[str] | None = None,
        schema: dict[str, Any] | None = None,
        strict_constrain_to_urls: bool = False,
        max_credits: int | None = None,
        model: str | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "prompt": prompt,
            "maxCredits": max_credits or self.settings.firecrawl_agent_max_credits,
            "model": model or self.settings.firecrawl_agent_model,
            "strictConstrainToURLs": strict_constrain_to_urls,
        }
        if urls:
            payload["urls"] = urls
        if schema:
            payload["schema"] = schema

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                "https://api.firecrawl.dev/v2/agent",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            job_id = data.get("id")
            if not job_id:
                raise RuntimeError("Firecrawl agent não retornou job id.")
            return job_id

    def get_agent_status(self, job_id: str) -> dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(
                f"https://api.firecrawl.dev/v2/agent/{job_id}",
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json()

    def wait_for_agent(
        self,
        job_id: str,
        *,
        timeout_seconds: int = 120,
        poll_interval_seconds: int = 2,
    ) -> dict[str, Any]:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            status_response = self.get_agent_status(job_id)
            status = status_response.get("status")
            if status == "completed":
                return status_response.get("data", {})
            if status == "failed":
                raise RuntimeError(status_response.get("error", "Firecrawl agent falhou."))
            time.sleep(poll_interval_seconds)
        raise TimeoutError("Timeout aguardando resultado do Firecrawl agent.")
