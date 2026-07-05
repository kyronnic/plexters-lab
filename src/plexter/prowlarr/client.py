"""Small Prowlarr API client for torrent metadata enrichment."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class ProwlarrHistoryRecord:
    download_id: str
    release_title: str
    indexer: str


class ProwlarrClient:
    """Client for the subset of Prowlarr history needed by /stalled."""

    def __init__(self, *, base_url: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.session = httpx.Client(timeout=10.0)

    def get_history_records(self) -> list[ProwlarrHistoryRecord]:
        if not self.api_key or not self.base_url:
            return []

        response = self.session.get(
            f"{self.base_url}/api/v1/history",
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
        return [history_record(row) for row in rows]

    def close(self) -> None:
        self.session.close()


def history_record(row: dict[str, Any]) -> ProwlarrHistoryRecord:
    data = row.get("data") if isinstance(row.get("data"), dict) else {}
    return ProwlarrHistoryRecord(
        download_id=text_value(
            row.get("downloadId"),
            data.get("downloadId"),
            data.get("torrentInfoHash"),
            data.get("infoHash"),
        ),
        release_title=text_value(
            row.get("sourceTitle"),
            row.get("title"),
            data.get("sourceTitle"),
            data.get("releaseTitle"),
            data.get("title"),
        ),
        indexer=text_value(
            row.get("indexer"),
            data.get("indexer"),
            data.get("indexerName"),
        ),
    )


def text_value(*values: Any) -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""
