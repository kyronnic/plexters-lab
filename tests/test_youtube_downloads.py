from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from plexter.services.youtube_downloads import (
    InvalidYouTubeUrlError,
    YouTubeDownloadConfigError,
    build_download_request,
    download_youtube,
    download_args,
    infer_download_type,
    is_youtube_url,
    sanitize_filename,
    season_directory_name,
)


def completed(stdout: str = "{}", returncode: int = 0, stderr: str = ""):
    return subprocess.CompletedProcess(
        args=["yt-dlp"],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


def test_is_youtube_url_accepts_youtube_hosts() -> None:
    assert is_youtube_url("https://www.youtube.com/watch?v=abc123") is True
    assert is_youtube_url("https://youtu.be/abc123") is True
    assert is_youtube_url("https://music.youtube.com/watch?v=abc123") is True


def test_is_youtube_url_rejects_non_youtube_hosts() -> None:
    assert is_youtube_url("https://example.com/watch?v=abc123") is False
    assert is_youtube_url("not a url") is False


def test_infer_download_type_uses_playlist_urls_for_tv() -> None:
    assert infer_download_type("https://www.youtube.com/playlist?list=PL123") == "tv"
    assert infer_download_type("https://www.youtube.com/watch?v=abc123") == "movie"
    assert infer_download_type("https://youtu.be/abc123") == "movie"


def test_infer_download_type_rejects_non_youtube_urls() -> None:
    with pytest.raises(InvalidYouTubeUrlError):
        infer_download_type("https://example.com/playlist?list=PL123")


def test_build_download_request_supports_type_override() -> None:
    request = build_download_request(
        url="https://www.youtube.com/watch?v=abc123",
        library_root="/tmp/youtube",
        requested_type="tv",
    )

    assert request.download_type == "tv"


def test_build_download_request_requires_library_root() -> None:
    with pytest.raises(YouTubeDownloadConfigError):
        build_download_request(
            url="https://www.youtube.com/watch?v=abc123",
            library_root="",
        )


def test_sanitize_filename_removes_path_characters() -> None:
    assert sanitize_filename('../Bad: Title/100% <x>') == "Bad Title 100 x"
    assert sanitize_filename("   ", fallback="Fallback") == "Fallback"


def test_season_directory_name_formats_and_validates() -> None:
    assert season_directory_name(1) == "Season 01"
    assert season_directory_name(12) == "Season 12"
    with pytest.raises(ValueError):
        season_directory_name(0)


def test_download_args_uses_single_file_format_without_ffmpeg() -> None:
    args = download_args(
        output_template="/tmp/video.%(ext)s",
        playlist_mode="--no-playlist",
        url="https://www.youtube.com/watch?v=abc123",
        ffmpeg_available=False,
    )

    assert args == [
        "-f",
        "best[ext=mp4][vcodec!=none][acodec!=none]/best[vcodec!=none][acodec!=none]",
        "--no-progress",
        "--no-playlist",
        "-o",
        "/tmp/video.%(ext)s",
        "https://www.youtube.com/watch?v=abc123",
    ]


def test_download_args_uses_merge_format_with_ffmpeg() -> None:
    args = download_args(
        output_template="/tmp/video.%(ext)s",
        playlist_mode="--yes-playlist",
        url="https://www.youtube.com/playlist?list=PL123",
        ffmpeg_available=True,
    )

    assert args == [
        "-f",
        "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format",
        "mp4",
        "--no-progress",
        "--yes-playlist",
        "-o",
        "/tmp/video.%(ext)s",
        "https://www.youtube.com/playlist?list=PL123",
    ]


def test_download_youtube_movie_builds_subprocess_args(tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def runner(args):
        calls.append(list(args))
        if "--dump-single-json" in args:
            return completed(json.dumps({"title": "My Video"}))
        return completed()

    request = build_download_request(
        url="https://www.youtube.com/watch?v=abc123",
        library_root=tmp_path,
    )

    result = download_youtube(request, runner=runner)

    assert result.download_type == "movie"
    assert result.destination == tmp_path / "Movies"
    assert calls[1] == [
        "-f",
        "best[ext=mp4][vcodec!=none][acodec!=none]/best[vcodec!=none][acodec!=none]",
        "--no-progress",
        "--no-playlist",
        "-o",
        str(tmp_path / "Movies" / "My Video [%(id)s].%(ext)s"),
        "https://www.youtube.com/watch?v=abc123",
    ]


def test_download_youtube_tv_builds_episode_template(tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def runner(args):
        calls.append(list(args))
        if "--dump-single-json" in args:
            return completed(
                json.dumps(
                    {
                        "title": "Learning Python",
                        "entries": [{"id": "one"}, {"id": "two"}],
                    }
                )
            )
        return completed()

    request = build_download_request(
        url="https://www.youtube.com/playlist?list=PL123",
        library_root=tmp_path,
        season=2,
    )

    result = download_youtube(request, runner=runner)

    assert result.download_type == "tv"
    assert result.destination == tmp_path / "TV" / "Learning Python" / "Season 02"
    assert calls[1][3] == "--yes-playlist"
    assert calls[1][5] == str(
        tmp_path
        / "TV"
        / "Learning Python"
        / "Season 02"
        / "S02E%(playlist_index)02d - %(title).200B [%(id)s].%(ext)s"
    )


def test_download_youtube_sanitizes_series_path(tmp_path: Path) -> None:
    def runner(args):
        if "--dump-single-json" in args:
            return completed(json.dumps({"title": "ignored", "entries": [{"id": "one"}]}))
        return completed()

    request = build_download_request(
        url="https://www.youtube.com/playlist?list=PL123",
        library_root=tmp_path,
        series="../Escaped/Series",
    )

    result = download_youtube(request, runner=runner)

    assert result.destination == tmp_path / "TV" / "Escaped Series" / "Season 01"
