"""qBittorrent Web API client."""

from __future__ import annotations

from dataclasses import dataclass
import httpx
from datetime import datetime, timedelta


@dataclass
class Torrent:
    """Represents a torrent from qBittorrent."""

    name: str
    state: str
    progress: float
    dl_speed: int
    up_speed: int
    added_on: int
    last_activity: int
    size: int
    downloaded: int
    uploaded: int
    ratio: float
    hash: str
    category: str = ""
    tags: str = ""
    tracker: str = ""
    raw_name: str = ""

    @property
    def time_since_activity(self) -> timedelta:
        """Get time since last activity."""
        if self.last_activity == -1:
            # Never had activity, use added_on
            return datetime.now() - datetime.fromtimestamp(self.added_on)
        return datetime.now() - datetime.fromtimestamp(self.last_activity)

    @property
    def is_stalled(self) -> bool:
        """Check if torrent is stalled."""
        stalled_states = [
            "stalledDL",
            "stalledUP",
            "forcedDL",
            "forcedUP",
            "missingFiles",
            "error",
        ]
        return self.state in stalled_states

    def is_inactive(self, hours: int = 48) -> bool:
        """Check if torrent has been inactive for specified hours."""
        threshold = datetime.now() - timedelta(hours=hours)
        last_activity_time = datetime.fromtimestamp(
            self.last_activity if self.last_activity != -1 else self.added_on
        )
        return last_activity_time < threshold


class QBittorrentClient:
    """Client for interacting with qBittorrent Web API."""

    def __init__(self, base_url: str, username: str, password: str) -> None:
        """Initialize qBittorrent client.

        Args:
            base_url: Base URL of qBittorrent (e.g., http://localhost:8080)
            username: qBittorrent username
            password: qBittorrent password
        """
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.session = httpx.Client(timeout=10.0)
        self._authenticated = False

    def authenticate(self) -> bool:
        """Authenticate with qBittorrent.

        Returns:
            True if authentication successful, False otherwise.
        """
        try:
            login_url = f"{self.base_url}/api/v2/auth/login"
            response = self.session.post(
                login_url,
                data={"username": self.username, "password": self.password},
            )
            # qBittorrent commonly returns 200 with "Ok."; tolerate 204 too.
            # The session cookie is automatically stored in the httpx client
            if response.status_code in {200, 204}:
                self._authenticated = True
                return True
            return False
        except httpx.RequestError as e:
            print(f"Authentication failed: {e}")
            return False

    def get_torrents(self, filter_: str = "all") -> list[Torrent]:
        """Get list of torrents.

        Args:
            filter_: Filter by state (all, downloading, seeding, completed, paused, active, inactive, stalled, etc.)

        Returns:
            List of Torrent objects.
        """
        if not self._authenticated:
            raise RuntimeError("Not authenticated with qBittorrent")

        try:
            torrents_url = f"{self.base_url}/api/v2/torrents/info"
            response = self.session.get(
                torrents_url,
                params={"filter": filter_},
            )
            response.raise_for_status()

            torrents = []
            for torrent_data in response.json():
                torrent = Torrent(
                    name=torrent_data.get("name", ""),
                    state=torrent_data.get("state", ""),
                    progress=torrent_data.get("progress", 0),
                    dl_speed=torrent_data.get("dl_speed", 0),
                    up_speed=torrent_data.get("up_speed", 0),
                    added_on=torrent_data.get("added_on", 0),
                    last_activity=torrent_data.get("last_activity", -1),
                    size=torrent_data.get("size", 0),
                    downloaded=torrent_data.get("downloaded", 0),
                    uploaded=torrent_data.get("uploaded", 0),
                    ratio=torrent_data.get("ratio", 0),
                    hash=torrent_data.get("hash", ""),
                    category=torrent_data.get("category", ""),
                    tags=torrent_data.get("tags", ""),
                    tracker=torrent_data.get("tracker", ""),
                    raw_name=torrent_data.get("name", ""),
                )
                torrents.append(torrent)

            return torrents
        except httpx.RequestError as e:
            raise RuntimeError(f"Failed to get torrents: {e}")

    def get_stalled_torrents(self) -> list[Torrent]:
        """Get list of stalled torrents.

        Returns:
            List of stalled Torrent objects.
        """
        if not self._authenticated:
            raise RuntimeError("Not authenticated with qBittorrent")

        try:
            torrents = self.get_torrents(filter_="stalled")
            return torrents
        except httpx.RequestError as e:
            raise RuntimeError(f"Failed to get stalled torrents: {e}")

    def get_inactive_torrents(self, hours: int = 48) -> list[Torrent]:
        """Get list of torrents inactive for specified hours.

        Args:
            hours: Number of hours to consider as threshold for inactivity.

        Returns:
            List of inactive Torrent objects.
        """
        if not self._authenticated:
            raise RuntimeError("Not authenticated with qBittorrent")

        try:
            torrents = self.get_torrents(filter_="all")
            threshold = datetime.now() - timedelta(hours=hours)
            inactive = []

            for torrent in torrents:
                last_activity_time = datetime.fromtimestamp(
                    torrent.last_activity
                    if torrent.last_activity != -1
                    else torrent.added_on
                )
                if last_activity_time < threshold:
                    inactive.append(torrent)

            return inactive
        except httpx.RequestError as e:
            raise RuntimeError(f"Failed to get inactive torrents: {e}")

    def close(self) -> None:
        """Close the session."""
        self.session.close()
