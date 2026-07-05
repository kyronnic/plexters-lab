"""Service for discovering stalled and inactive torrents."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import re
from typing import Literal

from plexter.arr.client import ArrClient, ArrRecord
from plexter.config import settings
from plexter.prowlarr.client import ProwlarrClient, ProwlarrHistoryRecord
from plexter.qbittorrent.client import QBittorrentClient, Torrent


MatchSource = Literal["radarr", "sonarr", "prowlarr", "qbittorrent"]
MediaKind = Literal["movie", "series", "unknown"]


@dataclass
class StalledTorrentInfo:
    """Information about a stalled torrent."""

    name: str
    display_name: str
    torrent_name: str
    info_hash: str
    state: str
    progress: float
    ratio: float
    added_on: datetime
    last_activity: datetime | None
    size_gb: float
    downloaded_gb: float
    time_inactive: timedelta
    source: Literal["qbittorrent"]
    media_kind: MediaKind = "unknown"
    arr_instance: str = ""
    arr_title: str = ""
    release_title: str = ""
    indexer: str = ""
    match_source: MatchSource = "qbittorrent"


def get_stalled_torrents(
    hours_inactive: int = 48,
) -> list[StalledTorrentInfo]:
    """Get stalled or inactive torrents from all available sources.

    Args:
        hours_inactive: Hours threshold for considering a torrent inactive

    Returns:
        List of stalled/inactive torrents with metadata
    """
    torrents: list[StalledTorrentInfo] = []

    # Get from qBittorrent
    try:
        qb_client = QBittorrentClient(
            base_url=settings.qbit_base_url,
            username=settings.qbit_user,
            password=settings.qbit_password,
        )

        try:
            if qb_client.authenticate():
                # Get stalled torrents
                stalled = qb_client.get_stalled_torrents()

                # Get inactive torrents
                inactive = qb_client.get_inactive_torrents(hours=hours_inactive)
                # Avoid duplicates with stalled
                stalled_hashes = {t.hash for t in stalled}
                for torrent in inactive:
                    if torrent.hash not in stalled_hashes:
                        stalled.append(torrent)

                torrents = enrich_torrents(stalled)
        finally:
            qb_client.close()
    except Exception as e:
        print(f"Failed to get torrents from qBittorrent: {e}")

    return torrents


def enrich_torrents(qbit_torrents: list[Torrent]) -> list[StalledTorrentInfo]:
    """Add best-effort Arr/Prowlarr metadata to qBittorrent torrents."""
    arr_records = get_arr_records()
    prowlarr_records = get_prowlarr_records()
    return [
        stalled_torrent_info(
            torrent,
            arr_match=find_arr_match(torrent, arr_records),
            prowlarr_match=find_prowlarr_match(torrent, prowlarr_records),
        )
        for torrent in qbit_torrents
    ]


def get_arr_records() -> list[ArrRecord]:
    records: list[ArrRecord] = []
    client_configs = [
        ("radarr", settings.radarr_instances),
        ("sonarr", settings.sonarr_instances),
    ]

    for kind, instances in client_configs:
        for instance in instances:
            if not instance.api_key:
                continue
            client = ArrClient(
                kind=kind,
                instance=instance.name,
                base_url=instance.base_url,
                api_key=instance.api_key,
            )
            try:
                records.extend(client.get_queue_records())
                records.extend(client.get_history_records())
            except Exception as exc:
                print(f"Failed to get {kind} metadata from {instance.name}: {exc}")
            finally:
                client.close()

    return records


def get_prowlarr_records() -> list[ProwlarrHistoryRecord]:
    if not settings.prowlarr_api_key:
        return []

    client = ProwlarrClient(
        base_url=settings.prowlarr_base_url,
        api_key=settings.prowlarr_api_key,
    )
    try:
        return client.get_history_records()
    except Exception as exc:
        print(f"Failed to get Prowlarr metadata: {exc}")
        return []
    finally:
        client.close()


def stalled_torrent_info(
    torrent: Torrent,
    *,
    arr_match: ArrRecord | None = None,
    prowlarr_match: ProwlarrHistoryRecord | None = None,
) -> StalledTorrentInfo:
    last_activity = (
        datetime.fromtimestamp(torrent.last_activity)
        if torrent.last_activity != -1
        else None
    )
    arr_title = arr_match.media_title if arr_match else ""
    release_title = ""
    indexer = ""
    match_source: MatchSource = "qbittorrent"
    media_kind: MediaKind = "unknown"
    arr_instance = ""

    if arr_match is not None:
        release_title = useful_text(arr_match.release_title, torrent) or (
            useful_text(prowlarr_match.release_title, torrent)
            if prowlarr_match is not None
            else ""
        )
        indexer = arr_match.indexer or (
            prowlarr_match.indexer if prowlarr_match is not None else ""
        )
        match_source = arr_match.kind
        media_kind = "movie" if arr_match.kind == "radarr" else "series"
        arr_instance = arr_match.instance
    elif prowlarr_match is not None:
        release_title = prowlarr_match.release_title
        indexer = prowlarr_match.indexer
        match_source = "prowlarr"

    display_name = first_text(
        useful_text(arr_title, torrent),
        useful_text(release_title, torrent),
        useful_text(torrent.name, torrent),
        torrent.hash,
    )

    return StalledTorrentInfo(
        name=display_name,
        display_name=display_name,
        torrent_name=torrent.name,
        info_hash=torrent.hash,
        state=torrent.state,
        progress=torrent.progress,
        ratio=torrent.ratio,
        added_on=datetime.fromtimestamp(torrent.added_on),
        last_activity=last_activity,
        size_gb=torrent.size / (1024**3),
        downloaded_gb=torrent.downloaded / (1024**3),
        time_inactive=torrent.time_since_activity,
        source="qbittorrent",
        media_kind=media_kind,
        arr_instance=arr_instance,
        arr_title=arr_title,
        release_title=release_title,
        indexer=indexer,
        match_source=match_source,
    )


def find_arr_match(torrent: Torrent, records: list[ArrRecord]) -> ArrRecord | None:
    matches = [
        record
        for record in records
        if record_matches_torrent(torrent, record.download_id, record.release_title)
    ]
    if not matches:
        return None

    return sorted(matches, key=lambda record: arr_record_score(torrent, record), reverse=True)[0]


def find_prowlarr_match(
    torrent: Torrent,
    records: list[ProwlarrHistoryRecord],
) -> ProwlarrHistoryRecord | None:
    for record in records:
        if record_matches_torrent(torrent, record.download_id, record.release_title):
            return record
    return None


def record_matches_torrent(
    torrent: Torrent,
    download_id: str,
    release_title: str,
) -> bool:
    hash_value = torrent.hash.lower()
    download_id_value = download_id.lower()
    if hash_value and download_id_value and hash_value in download_id_value:
        return True

    normalized_torrent_names = {
        normalize_title(value)
        for value in (torrent.name, torrent.raw_name)
        if normalize_title(value)
    }
    normalized_release = normalize_title(release_title)
    return bool(normalized_release and normalized_release in normalized_torrent_names)


def arr_record_score(torrent: Torrent, record: ArrRecord) -> int:
    score = 0
    if useful_text(record.media_title, torrent):
        score += 100
    if useful_text(record.release_title, torrent):
        score += 50
    if record.source == "history":
        score += 10
    if record.indexer:
        score += 1
    return score


def useful_text(value: str, torrent: Torrent) -> str:
    text = value.strip()
    if not text:
        return ""
    if is_hash_text(text, torrent.hash):
        return ""
    return text


def is_hash_text(value: str, torrent_hash: str) -> bool:
    normalized = value.strip().lower()
    if not normalized:
        return False
    if torrent_hash and normalized == torrent_hash.lower():
        return True
    return bool(re.fullmatch(r"[a-f0-9]{32,40}", normalized))


def normalize_title(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def first_text(*values: str) -> str:
    for value in values:
        text = value.strip()
        if text:
            return text
    return "Unknown torrent"


def format_stalled_torrents_message(torrents: list[StalledTorrentInfo]) -> str:
    """Format stalled torrents for Discord display.

    Args:
        torrents: List of stalled torrent info

    Returns:
        Formatted message string (under 2000 chars for Discord)
    """
    if not torrents:
        return "No stalled or inactive torrents found."

    lines = []
    lines.append(f"**Stalled/Inactive Torrents:** {len(torrents)} found\n")

    for torrent in sorted(torrents, key=lambda t: t.time_inactive, reverse=True)[:10]:
        # Compact format to fit Discord's 2000 char limit
        days = torrent.time_inactive.days
        hours = torrent.time_inactive.seconds // 3600

        title = truncate(torrent.display_name, 64)
        metadata = enrichment_label(torrent)
        line = (
            f"• **{title}**\n"
            f"  `{torrent.state}` {torrent.progress*100:.0f}% | "
            f"{days}d{hours}h | {torrent.ratio:.2f}r | {metadata}"
        )
        lines.append(line)

    if len(torrents) > 10:
        lines.append(f"\n_...and {len(torrents) - 10} more. Use `/stalled hours:24` for details._")

    return "\n".join(lines)


def enrichment_label(torrent: StalledTorrentInfo) -> str:
    if torrent.match_source in {"radarr", "sonarr"}:
        instance = f":{torrent.arr_instance}" if torrent.arr_instance else ""
        return f"{torrent.match_source}{instance}"
    if torrent.match_source == "prowlarr":
        return "prowlarr"
    if torrent.info_hash:
        return f"qbit:{torrent.info_hash[:8]}"
    return "qbit"


def truncate(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    return f"{value[: max_length - 3]}..."
