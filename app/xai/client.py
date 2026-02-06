from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

logger = logging.getLogger("xai.client")


class XAIClient:
    def __init__(self, base_url: str, api_key: str, timeout_s: float = 60.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout_s

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def create_response(
        self,
        *,
        model: str,
        input_messages: list[dict[str, Any]],
        tools: Optional[list[dict[str, Any]]] = None,
        response_format: Optional[dict[str, Any]] = None,
        store: bool = False,
        previous_response_id: Optional[str] = None,
        max_output_tokens: Optional[int] = None,
    ) -> dict[str, Any]:
        # xAI Enterprise API is compatible with OpenAI REST API; use /v1/responses
        payload: dict[str, Any] = {
            "model": model,
            "input": input_messages,
            "store": store,
        }
        if tools:
            payload["tools"] = tools
        if response_format:
            payload["response_format"] = response_format
        if previous_response_id:
            payload["previous_response_id"] = previous_response_id
        if max_output_tokens is not None:
            payload["max_output_tokens"] = max_output_tokens

        url = f"{self.base_url}/v1/responses"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(url, headers=self._headers(), json=payload)
            if r.status_code >= 400:
                logger.error("xAI error %s: %s", r.status_code, r.text[:2000])
                r.raise_for_status()
            return r.json()

    @staticmethod
    def extract_output_text(resp: dict[str, Any]) -> str:
        # OpenAI-style Responses API: resp.output[] contains messages; content may include output_text.
        out_parts: list[str] = []
        for item in resp.get("output", []) or []:
            if item.get("type") == "message":
                for c in item.get("content", []) or []:
                    if c.get("type") in ("output_text", "text"):
                        out_parts.append(c.get("text", ""))
        # Fallbacks (some SDKs use resp.content)
        if not out_parts and "content" in resp:
            return str(resp["content"])
        return "".join(out_parts).strip()
