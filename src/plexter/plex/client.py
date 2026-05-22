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

    def close(self) -> None:
        self.client.close()

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self.client.get(path, params=params)
        response.raise_for_status()
        return response.json()

    def get_server_identity(self) -> dict[str, Any]:
        return self.get("/identity")

    def get_libraries(self) -> list[dict[str, Any]]:
        data = self.get("/library/sections")
        return data.get("MediaContainer", {}).get("Directory", [])

    def get_libraries_by_type(self, library_type: str) -> list[dict[str, Any]]:
        return [
            library
            for library in self.get_libraries()
            if library.get("type") == library_type
        ]

    def find_library_by_title(self, title: str) -> dict[str, Any] | None:
        target = title.lower().strip()

        for library in self.get_libraries():
            if library.get("title", "").lower().strip() == target:
                return library

        return None

    def search_library(
        self,
        library_key: str | int,
        query: str,
    ) -> list[dict[str, Any]]:
        data = self.get(
            f"/library/sections/{library_key}/search",
            params={"query": query},
        )
        return data.get("MediaContainer", {}).get("Metadata", [])

    def search(self, query: str) -> list[dict[str, Any]]:
        data = self.get("/search", params={"query": query})
        return data.get("MediaContainer", {}).get("Metadata", [])

    def search_shows(
        self,
        query: str,
        library_title: str | None = None,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []

        for item in self.search(query):
            if item.get("type") != "show":
                continue

            if library_title and item.get("librarySectionTitle") != library_title:
                continue

            results.append(item)

        return results

    def get_metadata(self, rating_key: str | int) -> dict[str, Any]:
        data = self.get(f"/library/metadata/{rating_key}")
        metadata = data.get("MediaContainer", {}).get("Metadata", [])
        return metadata[0] if metadata else {}

    def get_children(self, rating_key: str | int) -> list[dict[str, Any]]:
        data = self.get(f"/library/metadata/{rating_key}/children")
        return data.get("MediaContainer", {}).get("Metadata", [])

    def get_show_seasons(self, show_rating_key: str | int) -> list[dict[str, Any]]:
        seasons = self.get_children(show_rating_key)
        return [
            season
            for season in seasons
            if season.get("type") == "season"
        ]

    def get_season_episodes(self, season_rating_key: str | int) -> list[dict[str, Any]]:
        episodes = self.get_children(season_rating_key)
        return sorted(
            [episode for episode in episodes if episode.get("type") == "episode"],
            key=lambda ep: (
                ep.get("parentIndex", 0),
                ep.get("index", 0),
                ep.get("title", ""),
            ),
        )

    def get_show_episodes(self, show_rating_key: str | int) -> list[dict[str, Any]]:
        episodes: list[dict[str, Any]] = []

        seasons = sorted(
            self.get_show_seasons(show_rating_key),
            key=lambda season: season.get("index", 0),
        )

        for season in seasons:
            season_key = season.get("ratingKey")
            if not season_key:
                continue

            episodes.extend(self.get_season_episodes(season_key))

        return episodes