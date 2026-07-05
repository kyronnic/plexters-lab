from __future__ import annotations

from datetime import datetime, timedelta

from plexter.arr.client import ArrRecord
from plexter.prowlarr.client import ProwlarrHistoryRecord
from plexter.qbittorrent.client import Torrent
from plexter.services import torrents as torrent_service


def torrent(
    *,
    name: str = "ABC123DEF456",
    hash: str = "ABC123DEF456",
) -> Torrent:
    return Torrent(
        name=name,
        state="metaDL",
        progress=0.0,
        dl_speed=0,
        up_speed=0,
        added_on=int((datetime.now() - timedelta(days=3)).timestamp()),
        last_activity=-1,
        size=0,
        downloaded=0,
        uploaded=0,
        ratio=0.0,
        hash=hash,
        category="sonarr",
        tags="",
        tracker="https://tracker.test/announce",
        raw_name=name,
    )


def test_arr_match_beats_prowlarr_match() -> None:
    qbit_torrent = torrent()
    arr = ArrRecord(
        kind="sonarr",
        instance="kids",
        download_id="abc123def456",
        title="Example.Show.S01E01",
        release_title="Example.Show.S01E01",
        media_title="Example Show - Pilot",
        indexer="Arr Indexer",
        source="queue",
    )
    prowlarr = ProwlarrHistoryRecord(
        download_id="abc123def456",
        release_title="Prowlarr.Release",
        indexer="Prowlarr Indexer",
    )

    enriched = torrent_service.stalled_torrent_info(
        qbit_torrent,
        arr_match=arr,
        prowlarr_match=prowlarr,
    )

    assert enriched.display_name == "Example Show - Pilot"
    assert enriched.match_source == "sonarr"
    assert enriched.media_kind == "series"
    assert enriched.arr_instance == "kids"
    assert enriched.release_title == "Example.Show.S01E01"
    assert enriched.indexer == "Arr Indexer"


def test_prowlarr_match_beats_qbittorrent_fallback() -> None:
    enriched = torrent_service.stalled_torrent_info(
        torrent(),
        prowlarr_match=ProwlarrHistoryRecord(
            download_id="abc123def456",
            release_title="Readable.Release.Name",
            indexer="Prowlarr Indexer",
        ),
    )

    assert enriched.display_name == "Readable.Release.Name"
    assert enriched.match_source == "prowlarr"
    assert enriched.indexer == "Prowlarr Indexer"


def test_unmatched_torrent_renders_hash_fallback() -> None:
    enriched = torrent_service.stalled_torrent_info(torrent(name="", hash="ABC123"))
    message = torrent_service.format_stalled_torrents_message([enriched])

    assert enriched.display_name == "ABC123"
    assert enriched.match_source == "qbittorrent"
    assert "qbit:ABC123" in message


def test_enrich_torrents_reports_matching_arr_instance(monkeypatch) -> None:
    monkeypatch.setattr(
        torrent_service,
        "get_arr_records",
        lambda: [
            ArrRecord(
                kind="radarr",
                instance="main",
                download_id="other",
                title="Other.Movie",
                release_title="Other.Movie",
                media_title="Other Movie",
                indexer="Indexer",
                source="history",
            ),
            ArrRecord(
                kind="radarr",
                instance="requests",
                download_id="abc123def456",
                title="Requested.Movie",
                release_title="Requested.Movie",
                media_title="Requested Movie",
                indexer="Indexer",
                source="queue",
            ),
        ],
    )
    monkeypatch.setattr(torrent_service, "get_prowlarr_records", lambda: [])

    enriched = torrent_service.enrich_torrents([torrent()])[0]

    assert enriched.display_name == "Requested Movie"
    assert enriched.match_source == "radarr"
    assert enriched.arr_instance == "requests"


def test_title_match_handles_metadata_available_in_qbittorrent() -> None:
    qbit_torrent = torrent(name="Example Show S01E01", hash="")
    record = ArrRecord(
        kind="sonarr",
        instance="main",
        download_id="",
        title="Example.Show.S01E01",
        release_title="Example.Show.S01E01",
        media_title="Example Show - Pilot",
        indexer="Indexer",
        source="history",
    )

    assert torrent_service.find_arr_match(qbit_torrent, [record]) == record


def test_hash_only_queue_match_uses_readable_history_title() -> None:
    qbit_torrent = torrent(hash="1977c6d6611d84dd1ec76fbdf5a778bb41fe9663")
    queue_record = ArrRecord(
        kind="sonarr",
        instance="requests",
        download_id="1977C6D6611D84DD1EC76FBDF5A778BB41FE9663",
        title="1977c6d6611d84dd1ec76fbdf5a778bb41fe9663",
        release_title="1977c6d6611d84dd1ec76fbdf5a778bb41fe9663",
        media_title="",
        indexer="TorrentDownload (Prowlarr)",
        source="queue",
    )
    history_record = ArrRecord(
        kind="sonarr",
        instance="requests",
        download_id="1977C6D6611D84DD1EC76FBDF5A778BB41FE9663",
        title="Greys Anatomy S03 FRENCH DVDRiP XviD TVrIders",
        release_title="Greys Anatomy S03 FRENCH DVDRiP XviD TVrIders",
        media_title="",
        indexer="TorrentDownload (Prowlarr)",
        source="history",
    )

    arr_match = torrent_service.find_arr_match(
        qbit_torrent,
        [queue_record, history_record],
    )
    enriched = torrent_service.stalled_torrent_info(
        qbit_torrent,
        arr_match=arr_match,
    )

    assert arr_match == history_record
    assert enriched.display_name == "Greys Anatomy S03 FRENCH DVDRiP XviD TVrIders"
    assert enriched.match_source == "sonarr"
