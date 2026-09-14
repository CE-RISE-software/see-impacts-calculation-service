"""Small client for the validation contract exposed by HEX Core."""

from __future__ import annotations

from typing import Any

import httpx


class HexCoreClient:
    """Validate a CE-RISE model payload without owning model validation locally."""

    def __init__(self, base_url: str, timeout_secs: int) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = httpx.Timeout(timeout_secs)

    def validation_url(self, model_family: str, model_version: str) -> str:
        return f"{self._base_url}/models/{model_family}/versions/{model_version}:validate"

    async def validate(
        self,
        *,
        model_family: str,
        model_version: str,
        payload: dict[str, Any],
        bearer_token: str | None = None,
    ) -> dict[str, Any]:
        headers = {}
        if bearer_token:
            headers["Authorization"] = f"Bearer {bearer_token}"

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                self.validation_url(model_family, model_version),
                headers=headers,
                json={"payload": payload},
            )
        response.raise_for_status()
        return response.json()
