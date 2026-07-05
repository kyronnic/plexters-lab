from __future__ import annotations

from unittest.mock import Mock

from plexter.arr.client import ArrClient


def test_radarr_queue_record_extracts_movie_metadata() -> None:
    client = ArrClient(
        kind="radarr",
        instance="main",
        base_url="http://radarr.test",
        api_key="key",
    )
    record = client._record_from_queue(
        {
            "downloadId": "ABC123",
            "title": "Release.Name.2026.1080p",
            "movie": {"title": "Release Name"},
            "indexer": "Indexer",
        }
    )

    assert record.kind == "radarr"
    assert record.instance == "main"
    assert record.download_id == "ABC123"
    assert record.release_title == "Release.Name.2026.1080p"
    assert record.media_title == "Release Name"
    assert record.indexer == "Indexer"


def test_sonarr_history_record_extracts_series_and_episode_metadata() -> None:
    client = ArrClient(
        kind="sonarr",
        instance="kids",
        base_url="http://sonarr.test",
        api_key="key",
    )
    record = client._record_from_history(
        {
            "data": {
                "downloadId": "XYZ789",
                "releaseTitle": "Example.Show.S01E01",
            },
            "series": {"title": "Example Show"},
            "episodes": [{"title": "Pilot"}],
            "indexer": "Indexer",
        }
    )

    assert record.kind == "sonarr"
    assert record.instance == "kids"
    assert record.download_id == "XYZ789"
    assert record.release_title == "Example.Show.S01E01"
    assert record.media_title == "Example Show - Pilot"
    assert record.indexer == "Indexer"


def test_get_queue_records_handles_paged_api_shape() -> None:
    client = ArrClient(
        kind="radarr",
        instance="main",
        base_url="http://radarr.test",
        api_key="key",
    )
    response = Mock()
    response.json.return_value = {
        "records": [
            {
                "downloadId": "ABC123",
                "title": "Release.Name.2026.1080p",
                "movie": {"title": "Release Name"},
            }
        ]
    }
    client.session = Mock()
    client.session.get.return_value = response

    records = client.get_queue_records()

    assert records[0].download_id == "ABC123"
    client.session.get.assert_called_once()
