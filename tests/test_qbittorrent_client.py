"""Tests for qBittorrent client."""

from __future__ import annotations

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from plexter.qbittorrent.client import QBittorrentClient, Torrent


@pytest.fixture
def mock_torrent_data():
    """Sample torrent data from qBittorrent API."""
    return [
        {
            "name": "Example Show S01E01",
            "state": "stalledDL",
            "progress": 0.95,
            "dl_speed": 0,
            "up_speed": 0,
            "added_on": int((datetime.now() - timedelta(days=5)).timestamp()),
            "last_activity": int((datetime.now() - timedelta(days=3)).timestamp()),
            "size": 5 * 1024**3,
            "downloaded": 4.75 * 1024**3,
            "uploaded": 0,
            "ratio": 0.0,
            "hash": "abc123def456",
            "category": "sonarr",
            "tags": "priority",
            "tracker": "https://tracker.test/announce",
        },
        {
            "name": "Another Show S02E05",
            "state": "seeding",
            "progress": 1.0,
            "dl_speed": 0,
            "up_speed": 100000,
            "added_on": int((datetime.now() - timedelta(days=2)).timestamp()),
            "last_activity": int(datetime.now().timestamp()),
            "size": 8 * 1024**3,
            "downloaded": 8 * 1024**3,
            "uploaded": 16 * 1024**3,
            "ratio": 2.0,
            "hash": "xyz789uvw456",
            "category": "radarr",
            "tags": "",
            "tracker": "https://tracker.test/announce",
        },
    ]


class TestTorrent:
    """Test Torrent dataclass."""

    def test_torrent_creation(self, mock_torrent_data):
        """Test creating a Torrent instance."""
        data = mock_torrent_data[0]
        torrent = Torrent(
            name=data["name"],
            state=data["state"],
            progress=data["progress"],
            dl_speed=data["dl_speed"],
            up_speed=data["up_speed"],
            added_on=data["added_on"],
            last_activity=data["last_activity"],
            size=data["size"],
            downloaded=data["downloaded"],
            uploaded=data["uploaded"],
            ratio=data["ratio"],
            hash=data["hash"],
        )

        assert torrent.name == "Example Show S01E01"
        assert torrent.state == "stalledDL"
        assert torrent.hash == "abc123def456"

    def test_is_stalled(self, mock_torrent_data):
        """Test stalled state detection."""
        stalled_data = mock_torrent_data[0]
        stalled = Torrent(
            name=stalled_data["name"],
            state="stalledDL",
            progress=0.95,
            dl_speed=0,
            up_speed=0,
            added_on=stalled_data["added_on"],
            last_activity=stalled_data["last_activity"],
            size=stalled_data["size"],
            downloaded=stalled_data["downloaded"],
            uploaded=stalled_data["uploaded"],
            ratio=stalled_data["ratio"],
            hash=stalled_data["hash"],
        )

        assert stalled.is_stalled is True

    def test_time_since_activity(self, mock_torrent_data):
        """Test time_since_activity calculation."""
        data = mock_torrent_data[0]
        torrent = Torrent(
            name=data["name"],
            state=data["state"],
            progress=data["progress"],
            dl_speed=data["dl_speed"],
            up_speed=data["up_speed"],
            added_on=data["added_on"],
            last_activity=data["last_activity"],
            size=data["size"],
            downloaded=data["downloaded"],
            uploaded=data["uploaded"],
            ratio=data["ratio"],
            hash=data["hash"],
        )

        time_since = torrent.time_since_activity
        assert time_since.days >= 2  # Should be approximately 3 days


class TestQBittorrentClient:
    """Test QBittorrentClient."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return QBittorrentClient(
            base_url="http://localhost:8080",
            username="admin",
            password="admin",
        )

    @patch("plexter.qbittorrent.client.httpx.Client")
    def test_authenticate_success(self, mock_session_class, client):
        """Test successful authentication."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_session = Mock()
        mock_session.post.return_value = mock_response
        client.session = mock_session

        result = client.authenticate()

        assert result is True
        assert client._authenticated is True
        mock_session.post.assert_called_once()

    @patch("plexter.qbittorrent.client.httpx.Client")
    def test_authenticate_failure(self, mock_session_class, client):
        """Test failed authentication."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_session = Mock()
        mock_session.post.return_value = mock_response
        client.session = mock_session

        result = client.authenticate()

        assert result is False
        assert client._authenticated is False

    def test_get_torrents_not_authenticated(self, client):
        """Test that get_torrents raises error when not authenticated."""
        with pytest.raises(RuntimeError, match="Not authenticated"):
            client.get_torrents()

    @patch("plexter.qbittorrent.client.httpx.Client")
    def test_get_torrents_success(self, mock_session_class, client, mock_torrent_data):
        """Test successful torrent retrieval."""
        client._authenticated = True
        mock_response = Mock()
        mock_response.json.return_value = mock_torrent_data
        mock_session = Mock()
        mock_session.get.return_value = mock_response
        client.session = mock_session

        torrents = client.get_torrents()

        assert len(torrents) == 2
        assert torrents[0].name == "Example Show S01E01"
        assert torrents[1].name == "Another Show S02E05"
        assert torrents[0].category == "sonarr"
        assert torrents[0].tags == "priority"
        assert torrents[0].tracker == "https://tracker.test/announce"
        assert torrents[0].raw_name == "Example Show S01E01"

    @patch("plexter.qbittorrent.client.httpx.Client")
    def test_get_torrents_keeps_metadata_less_identifiers(self, mock_session_class, client):
        """Test metadata-less torrents keep qBittorrent matching fields."""
        client._authenticated = True
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "name": "abc123def456",
                "state": "metaDL",
                "progress": 0,
                "hash": "abc123def456",
                "category": "sonarr",
                "tags": "",
                "tracker": "https://tracker.test/announce",
            }
        ]
        mock_session = Mock()
        mock_session.get.return_value = mock_response
        client.session = mock_session

        torrents = client.get_torrents()

        assert torrents[0].name == "abc123def456"
        assert torrents[0].hash == "abc123def456"
        assert torrents[0].category == "sonarr"
        assert torrents[0].tracker == "https://tracker.test/announce"

    @patch("plexter.qbittorrent.client.httpx.Client")
    def test_get_stalled_torrents(self, mock_session_class, client, mock_torrent_data):
        """Test getting stalled torrents."""
        client._authenticated = True
        stalled_data = [mock_torrent_data[0]]  # Only the stalled one

        mock_response = Mock()
        mock_response.json.return_value = stalled_data
        mock_session = Mock()
        mock_session.get.return_value = mock_response
        client.session = mock_session

        torrents = client.get_stalled_torrents()

        assert len(torrents) == 1
        assert torrents[0].state == "stalledDL"

    def test_close_session(self, client):
        """Test closing the session."""
        mock_session = Mock()
        client.session = mock_session

        client.close()

        mock_session.close.assert_called_once()
