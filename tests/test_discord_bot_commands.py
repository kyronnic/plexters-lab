from pathlib import Path

from plexter.discord_bot.commands import (
    format_libraries,
    format_recent_activity,
    format_show_search_results,
    format_system_status,
    format_youtube_download_error,
    format_youtube_download_queued,
    format_youtube_download_success,
)
from plexter.services.health import PlexHealth, ServiceCheck, SystemStatus
from plexter.services.youtube_downloads import DownloadResult


def test_format_libraries_lists_titles_and_types() -> None:
    assert format_libraries(
        [
            {"title": "TV", "type": "show"},
            {"title": "Movies", "type": "movie"},
        ]
    ) == "- TV (show)\n- Movies (movie)"


def test_format_libraries_handles_empty_list() -> None:
    assert format_libraries([]) == "No Plex libraries found."


def test_format_show_search_results_lists_top_shows() -> None:
    assert format_show_search_results(
        "frieren",
        [
            {"title": "Frieren: Beyond Journey's End"},
            {"title": "Frieren"},
        ],
    ) == "- Frieren: Beyond Journey's End\n- Frieren"


def test_format_show_search_results_handles_empty_list() -> None:
    assert format_show_search_results("missing", []) == "No shows found for 'missing'."


def test_format_system_status_is_concise() -> None:
    status = SystemStatus(
        atlas_online=True,
        plex=PlexHealth(
            name="Plex",
            connected=True,
            message="Connected",
            library_count=4,
        ),
        postgres=ServiceCheck(
            name="Postgres",
            connected=False,
            message="postgres unavailable",
        ),
    )

    assert format_system_status(status) == (
        "Atlas: Online\n"
        "Plex: Connected\n"
        "Postgres: Failed\n"
        "Libraries: 4"
    )


def test_format_recent_activity_shows_latest_items() -> None:
    assert format_recent_activity(
        [
            {"summary": "round_robin - success - Created playlist"},
            {"summary": "success - sent - Discord sent"},
        ]
    ) == (
        "- round_robin - success - Created playlist\n"
        "- success - sent - Discord sent"
    )


def test_format_recent_activity_handles_empty_list() -> None:
    assert format_recent_activity([]) == "No recent Plexter activity."


def test_format_youtube_download_queued_uses_inferred_library() -> None:
    assert format_youtube_download_queued("movie") == (
        "Queued YouTube download for YouTube Movies."
    )
    assert format_youtube_download_queued("tv") == (
        "Queued YouTube download for YouTube TV."
    )


def test_format_youtube_download_success_includes_destination() -> None:
    result = DownloadResult(
        download_type="movie",
        destination=Path("/mnt/media/Library/YouTube/Movies"),
        display_name="Movies",
    )

    assert format_youtube_download_success(result) == (
        "Downloaded to YouTube Movies: /mnt/media/Library/YouTube/Movies"
    )


def test_format_youtube_download_error_is_concise() -> None:
    assert format_youtube_download_error(ValueError("bad url")) == (
        "YouTube download failed: bad url"
    )
