"""Small Radarr/Sonarr API clients for torrent metadata enrichment."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import httpx


ArrKind = Literal["radarr", "sonarr"]


@dataclass(frozen=True)
class ArrRecord:
    kind: ArrKind
    instance: str
    download_id: str
    title: str
    release_title: str
    media_title: str
    indexer: str
    source: Literal["queue", "history"]


class ArrClient:
    """Client for the subset of Radarr/Sonarr APIs needed by /stalled."""

    def __init__(
        self,
        *,
        kind: ArrKind,
        instance: str,
        base_url: str,
        api_key: str,
    ) -> None:
        self.kind = kind
        self.instance = instance
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.session = httpx.Client(timeout=10.0)

    def get_queue_records(self) -> list[ArrRecord]:
        if not self.api_key or not self.base_url:
            return []

        response = self.session.get(
            f"{self.base_url}/api/v3/queue",
            params={
                "apikey": self.api_key,
                "page": 1,
                "pageSize": 250,
                "includeUnknownMovieItems": "true",
                "includeUnknownSeriesItems": "true",
            },
        )
        response.raise_for_status()
        payload = response.json()
        rows = payload.get("records", payload if isinstance(payload, list) else [])
        return [self._record_from_queue(row) for row in rows]

    def get_history_records(self) -> list[ArrRecord]:
        if not self.api_key or not self.base_url:
            return []

        response = self.session.get(
            f"{self.base_url}/api/v3/history",
            params={
                "apikey": self.api_key,
                "page": 1,
                "pageSize": 250,
                "sortKey": "date",
                "sortDirection": "descending",
            },
        )
        response.raise_for_status()
        payload = response.json()
        rows = payload.get("records", payload if isinstance(payload, list) else [])
        return [self._record_from_history(row) for row in rows]

    def close(self) -> None:
        self.session.close()

    def _record_from_queue(self, row: dict[str, Any]) -> ArrRecord:
        release_title = text_value(
            row.get("title"),
            row.get("sourceTitle"),
            row.get("downloadTitle"),
        )
        return ArrRecord(
            kind=self.kind,
            instance=self.instance,
            download_id=text_value(row.get("downloadId"), row.get("download_id")),
            title=release_title,
            release_title=release_title,
            media_title=self._media_title(row),
            indexer=text_value(row.get("indexer")),
            source="queue",
        )

    def _record_from_history(self, row: dict[str, Any]) -> ArrRecord:
        data = row.get("data") if isinstance(row.get("data"), dict) else {}
        release_title = text_value(
            row.get("sourceTitle"),
            row.get("downloadTitle"),
            data.get("releaseTitle"),
            data.get("sourceTitle"),
            data.get("downloadTitle"),
        )
        return ArrRecord(
            kind=self.kind,
            instance=self.instance,
            download_id=text_value(
                row.get("downloadId"),
                data.get("downloadId"),
                data.get("torrentInfoHash"),
            ),
            title=release_title,
            release_title=release_title,
            media_title=self._media_title(row),
            indexer=text_value(row.get("indexer"), data.get("indexer")),
            source="history",
        )

    def _media_title(self, row: dict[str, Any]) -> str:
        if self.kind == "radarr":
            movie = row.get("movie") if isinstance(row.get("movie"), dict) else {}
            return text_value(movie.get("title"), row.get("movieTitle"))

        series = row.get("series") if isinstance(row.get("series"), dict) else {}
        episodes = row.get("episodes") if isinstance(row.get("episodes"), list) else []
        episode_titles = [
            text_value(episode.get("title"))
            for episode in episodes
            if isinstance(episode, dict) and text_value(episode.get("title"))
        ]
        series_title = text_value(series.get("title"), row.get("seriesTitle"))
        if series_title and episode_titles:
            return f"{series_title} - {', '.join(episode_titles[:2])}"
        return series_title


def text_value(*values: Any) -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""
