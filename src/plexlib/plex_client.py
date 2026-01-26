from __future__ import annotations

import os
import httpx
from typing import Dict
from dotenv import load_dotenv

from plexlib.plex_jwt_auth import get_plex_token, _base_headers

load_dotenv()

def _require_env(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise RuntimeError(f"{name} is not set")
    return val

def _server_base_url() -> str:
    base = _require_env("PLEX_SERVER_URL")
    return base.rstrip("/")

def plex_headers() -> Dict[str, str]:
    client_id = _require_env("PLEX_CLIENT_ID")

    token = get_plex_token().strip()
    headers = _base_headers(client_id).copy()
    headers["X-Plex-Token"] = token
    headers["Accept"] = "application/xml"
    return headers

def plex_get(path: str, *, params: dict | None = None) -> httpx.Response:
    base = _server_base_url()
    headers = plex_headers()
    resp = httpx.get(f"{base}{path}", headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    return resp