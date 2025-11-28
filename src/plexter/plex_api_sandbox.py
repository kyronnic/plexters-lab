from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List

import httpx
import xml.etree.ElementTree as ET

from plexter.plex_jwt_auth import PLEX_LEGACY_TOKEN, _base_headers

PLEX_SERVER_URL = os.getenv("PLEX_SERVER_URL")

@dataclass
class EpisodeSummary:
    show_title: str
    season_index: int
    episode_index: int
    episode_title: str
    air_date: str
    rating_key: str
    library_section_title: str

def _server_base_url() -> str:
    if not PLEX_SERVER_URL:
        raise RuntimeError(
            "PLEX_SERVER_URL is not set. Add it to the .env"
        )
    return PLEX_SERVER_URL.rstrip("/")

def _server_headers() -> dict:
    if not PLEX_LEGACY_TOKEN:
        raise RuntimeError("PLEX_LEGACY_TOKEN not set in .env")
    headers = _base_headers().copy()
    headers["X-Plex-Token"] = PLEX_LEGACY_TOKEN
    headers["Accept"] = "application/xml"
    return headers

def get_tv_sections() -> List[dict]:
    base = _server_base_url()
    headers = _server_headers()

    resp = httpx.get(f"{base}/library/sections", headers=headers, timeout=10)
    resp.raise_for_status()

    root = ET.fromstring(resp.text)
    sections: List[dict] = []

    for dir_el in root.findall("Directory"):
        if dir_el.get("type") == "show":
            sections.append(
                {
                    "key": dir_el.get("key"),
                    "title": dir_el.get("title") or ""
                }
            )

    return sections

def get_episodes_for_year(year: int) -> List[EpisodeSummary]:
    base = _server_base_url()
    headers = _server_headers()

    start = f"{year}-01-01"
    end = f"{year}-12-31"

    episodes: List[EpisodeSummary] = []

    sections = get_tv_sections()
    if not sections:
        print("No TV sections found on this server")

    for section in sections:
        section_key = section["key"]
        section_title = section["title"]

        url = f"{base}/library/sections/{section_key}/all"

        params = {
            "type": 4,
            "originallyAvailableAt>=": start,
            "originallyAvailableAt<=": end
        }

        resp = httpx.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()

        root = ET.fromstring(resp.text)

        for video in root.findall("Video"):
            episodes.append(
                EpisodeSummary(
                    show_title=video.get("grandparentTitle", ""),
                    season_index=int(video.get("parentIndex", "0") or 0),
                    episode_index=int(video.get("index", "0") or 0),
                    episode_title=video.get("title", ""),
                    air_date=video.get("originallyAvailableAt", ""),
                    rating_key=video.get("ratingKey", ""),
                    library_section_title=section_title
                )
            )
    return episodes

if __name__ == "__main__":
    episodes = get_episodes_for_year(2016)
    print(f"Found {len(episodes)} episodes released in 2016.\n")
    for ep in episodes[:50]:
        print(
            f"[{ep.library_section_title}] "
            f"{ep.show_title} "
            f"S{ep.season_index:02d}E{ep.episode_index:02d} - "
            f"{ep.episode_title} "
            f"({ep.air_date})"
        )