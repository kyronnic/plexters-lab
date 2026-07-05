from __future__ import annotations

from unittest.mock import Mock

from plexter.prowlarr.client import ProwlarrClient, history_record


def test_history_record_extracts_nested_metadata() -> None:
    record = history_record(
        {
            "data": {
                "downloadId": "ABC123",
                "releaseTitle": "Example.Movie.2026.1080p",
                "indexerName": "Indexer",
            }
        }
    )

    assert record.download_id == "ABC123"
    assert record.release_title == "Example.Movie.2026.1080p"
    assert record.indexer == "Indexer"


def test_get_history_records_handles_paged_api_shape() -> None:
    client = ProwlarrClient(base_url="http://prowlarr.test", api_key="key")
    response = Mock()
    response.json.return_value = {
        "records": [
            {
                "downloadId": "ABC123",
                "sourceTitle": "Example.Movie.2026.1080p",
                "indexer": "Indexer",
            }
        ]
    }
    client.session = Mock()
    client.session.get.return_value = response

    records = client.get_history_records()

    assert records[0].download_id == "ABC123"
    assert records[0].release_title == "Example.Movie.2026.1080p"
    client.session.get.assert_called_once()
