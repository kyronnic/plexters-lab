from typing import Any

import httpx

from plexter.config import settings


class PlexClient:
    def __init__(
        self,
        base_url: str | None = None,
        token: str | None = None,
        timeout: float = 15.0,
    ) -> None:
        self.base_url = (base_url or settings.plex_base_url).rstrip("/")
        self.token = token or settings.plex_token
        self.timeout = timeout

        if not self.base_url:
            raise ValueError("PLEX_BASE_URL is not set.")
        if not self.token:
            raise ValueError("PLEX_TOKEN is not set.")

        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={
                "Accept": "application/json",
                "X-Plex-Token": self.token,
            },
        )

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self.client.get(path, params=params)
        response.raise_for_status()
        return response.json()

    def get_server_identity(self) -> dict[str, Any]:
        return self.get("/identity")

    def get_libraries(self) -> list[dict[str, Any]]:
        data = self.get("/library/sections")
        return data.get("MediaContainer", {}).get("Directory", [])

    def close(self) -> None:
        self.client.close()