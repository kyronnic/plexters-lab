from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import List, Optional

from plexlib.plex_client import plex_get

def get_machine_id() -> str:
    resp = plex_get("/identity")
    root = ET.fromstring(resp.text)
    mid = root.get("machineIdentifier")
    if not mid:
        raise RuntimeError("Could not read machineIdentifier from /identity")
    return mid

def create_video_playlist(title: str, episode_rating_keys: List[str]) -> None:
    if not episode_rating_keys:
        raise ValueError("No episode keys provided")

    machine_id = get_machine_id()

    keys_csv = ",".join(episode_rating_keys)
    uri = f"server://{machine_id}/com.plexapp.plugins.library/library/metadata/{keys_csv}"

    plex_get(
        "/playlists",
        params={
            "type": "video",
            "title": title,
            "uri": uri
        }
    )