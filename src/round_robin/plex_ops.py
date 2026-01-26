from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
import xml.etree.ElementTree as ET

from plexlib.plex_client import plex_get


@dataclass(frozen=True)
class TvSection:
    key: str
    title: str

@dataclass(frozen=True)
class ShowHit:
    rating_key: str
    title: str
    year: Optional[int] = None

@dataclass(frozen=True)
class Episode:
    rating_key: str
    show_title: str
    season_index: int
    episode_index: int
    title: str

def _xml_root(resp_text: str) -> ET.Element:
    return ET.fromstring(resp_text)

def get_tv_sections() -> List[TvSection]:
    resp = plex_get("/library/sections")
    root = _xml_root(resp.text)

    out: List[TvSection] = []
    for d in root.findall("Directory"):
        if d.get("type") == "show":
            k = d.get("key") or ""
            t = d.get("title") or ""
            if k:
                out.append(TvSection(key=k, title=t))
    return out

def search_shows(section_key: str, query: str, limit: int = 25) -> List[ShowHit]:
    resp = plex_get(
        f"/library/sections/{section_key}/search",
        params={"type": 2, "query": query}
    )
    root = _xml_root(resp.text)

    hits: List[ShowHit] = []
    for d in root.findall("Directory"):
        rk = d.get("ratingKey")
        title = d.get("title")
        if rk and title:
            year_raw = d.get("year")
            year = int(year_raw) if year_raw and year_raw.isdigit() else None
            hits.append(ShowHit(rating_key=rk, title=title, year=year))
    return hits[:limit]

def fetch_show_episodes(show_rating_key: str) -> List[Episode]:
    resp = plex_get(f"/library/metadata/{show_rating_key}/allLeaves")
    root = _xml_root(resp.text)

    episodes: List[Episode] = []
    for v in root.findall("Video"):
        rk = v.get("ratingKey") or ""
        show_title = v.get("grandparentTitle") or ""
        season = int(v.get("parentIndex") or 0)
        ep = int(v.get("index") or 0)
        title = v.get("title") or ""
        if rk:
            episodes.append(
                Episode(
                    rating_key=rk,
                    show_title=show_title,
                    season_index=season,
                    episode_index=ep,
                    title=title
                )
            )

    episodes.sort(key=lambda e: (e.season_index, e.episode_index, int(e.rating_key)))
    return episodes

def format_episode_line(ep: Episode) -> str:
    return f"{ep.show_title} - S{ep.season_index:02d}E{ep.episode_index:02d} — {ep.title}"