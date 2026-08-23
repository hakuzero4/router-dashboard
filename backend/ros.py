from __future__ import annotations

from typing import Any

import httpx


class RouterOS:
    def __init__(self, base_url: str, username: str, password: str) -> None:
        self.base = base_url.rstrip("/")
        self.client = httpx.AsyncClient(
            base_url=self.base,
            auth=(username, password),
            timeout=httpx.Timeout(12.0, connect=4.0),
            headers={"Accept": "application/json"},
        )

    async def get(self, path: str) -> Any:
        r = await self.client.get("/rest" + path)
        r.raise_for_status()
        return r.json()

    async def get_list(self, path: str) -> list[Any]:
        try:
            data = await self.get(path)
        except httpx.HTTPError:
            return []
        return data if isinstance(data, list) else []

    async def close(self) -> None:
        await self.client.aclose()
