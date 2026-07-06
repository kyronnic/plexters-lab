from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Literal
from urllib.parse import parse_qs, urlparse


DownloadType = Literal["movie", "tv"]
Runner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]

YOUTUBE_MERGE_FORMAT = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
YOUTUBE_SINGLE_FILE_FORMAT = (
    "best[ext=mp4][vcodec!=none][acodec!=none]/best[vcodec!=none][acodec!=none]"
)
YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
}
DEFAULT_LIBRARY_ROOT = "/mnt/media/Library/YouTube"


class YouTubeDownloadError(Exception):
    """Base error for YouTube download operations."""


class InvalidYouTubeUrlError(YouTubeDownloadError):
    """Raised when the provided URL is not a supported YouTube URL."""


class YouTubeDownloadConfigError(YouTubeDownloadError):
    """Raised when required YouTube download configuration is missing."""


@dataclass(frozen=True)
class DownloadRequest:
    url: str
    library_root: Path
    download_type: DownloadType
    title: str | None = None
    series: str | None = None
    season: int = 1


@dataclass(frozen=True)
class DownloadResult:
    download_type: DownloadType
    destination: Path
    display_name: str


def is_youtube_url(url: str) -> bool:
    parsed = urlparse(url.strip())
    return parsed.scheme in {"http", "https"} and parsed.netloc.lower() in YOUTUBE_HOSTS


def validate_youtube_url(url: str) -> None:
    if not is_youtube_url(url):
        raise InvalidYouTubeUrlError("Only YouTube and YouTube Music URLs are supported.")


def infer_download_type(url: str) -> DownloadType:
    validate_youtube_url(url)
    parsed = urlparse(url.strip())
    query = parse_qs(parsed.query)

    if parsed.path.rstrip("/") == "/playlist" and query.get("list"):
        return "tv"
    if query.get("list") and not query.get("v"):
        return "tv"
    return "movie"


def resolve_download_type(url: str, requested_type: str | None) -> DownloadType:
    if requested_type is None or not requested_type.strip():
        return infer_download_type(url)

    normalized = requested_type.strip().lower()
    if normalized not in {"movie", "tv"}:
        raise ValueError("type must be either 'movie' or 'tv'.")
    return normalized  # type: ignore[return-value]


def sanitize_filename(value: str | None, *, fallback: str = "Untitled") -> str:
    sanitized = (value or "").strip()
    sanitized = re.sub(r"[\\/:*?\"<>|%]+", " ", sanitized)
    sanitized = re.sub(r"\s+", " ", sanitized)
    sanitized = sanitized.strip(" .")
    if not sanitized:
        return fallback
    return sanitized[:180].rstrip(" .") or fallback


def season_directory_name(season: int) -> str:
    if season < 1:
        raise ValueError("season must be 1 or greater.")
    return f"Season {season:02d}"


def ensure_inside_root(root: Path, destination: Path) -> None:
    resolved_root = root.resolve(strict=False)
    resolved_destination = destination.resolve(strict=False)
    if not resolved_destination.is_relative_to(resolved_root):
        raise YouTubeDownloadConfigError("Resolved destination escaped YouTube library root.")


def default_runner(args: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "yt_dlp", *args],
        check=False,
        capture_output=True,
        text=True,
    )


def run_yt_dlp(args: Sequence[str], runner: Runner = default_runner) -> str:
    result = runner(args)
    if result.returncode != 0:
        message = (result.stderr or result.stdout or "yt-dlp failed.").strip()
        raise YouTubeDownloadError(message.splitlines()[-1])
    return result.stdout


def has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def download_args(
    *,
    output_template: str,
    playlist_mode: str,
    url: str,
    ffmpeg_available: bool | None = None,
) -> list[str]:
    if ffmpeg_available is None:
        ffmpeg_available = has_ffmpeg()

    args = [
        "-f",
        YOUTUBE_MERGE_FORMAT if ffmpeg_available else YOUTUBE_SINGLE_FILE_FORMAT,
    ]
    if ffmpeg_available:
        args.extend(["--merge-output-format", "mp4"])
    args.extend(
        [
            "--no-progress",
            playlist_mode,
            "-o",
            output_template,
            url,
        ]
    )
    return args


def inspect_youtube_metadata(url: str, runner: Runner = default_runner) -> dict[str, object]:
    validate_youtube_url(url)
    output = run_yt_dlp(
        [
            "--dump-single-json",
            "--flat-playlist",
            "--no-warnings",
            url,
        ],
        runner=runner,
    )
    try:
        metadata = json.loads(output)
    except json.JSONDecodeError as exc:
        raise YouTubeDownloadError("Could not parse yt-dlp metadata output.") from exc
    if not isinstance(metadata, dict):
        raise YouTubeDownloadError("yt-dlp returned unexpected metadata output.")
    return metadata


def build_download_request(
    *,
    url: str,
    library_root: str | Path,
    requested_type: str | None = None,
    title: str | None = None,
    series: str | None = None,
    season: int | None = None,
) -> DownloadRequest:
    if not str(library_root).strip():
        raise YouTubeDownloadConfigError("YOUTUBE_LIBRARY_ROOT is not set.")

    resolved_season = season or 1
    return DownloadRequest(
        url=url,
        library_root=Path(library_root).expanduser(),
        download_type=resolve_download_type(url, requested_type),
        title=title,
        series=series,
        season=resolved_season,
    )


def movie_output_template(request: DownloadRequest, metadata: dict[str, object]) -> tuple[Path, str]:
    destination = request.library_root / "Movies"
    ensure_inside_root(request.library_root, destination)
    display_name = sanitize_filename(
        request.title or str(metadata.get("title") or ""),
        fallback="YouTube Video",
    )
    return destination, str(destination / f"{display_name} [%(id)s].%(ext)s")


def tv_output_template(request: DownloadRequest, metadata: dict[str, object]) -> tuple[Path, str, str]:
    series_name = sanitize_filename(
        request.series or str(metadata.get("title") or ""),
        fallback="YouTube Playlist",
    )
    destination = request.library_root / "TV" / series_name / season_directory_name(request.season)
    ensure_inside_root(request.library_root, destination)

    entries = metadata.get("entries")
    is_playlist = isinstance(entries, list) and len(entries) > 0
    episode_token = "%(playlist_index)02d" if is_playlist else "01"
    output_template = str(
        destination
        / f"S{request.season:02d}E{episode_token} - %(title).200B [%(id)s].%(ext)s"
    )
    return destination, output_template, series_name


def download_youtube(
    request: DownloadRequest,
    *,
    runner: Runner = default_runner,
) -> DownloadResult:
    metadata = inspect_youtube_metadata(request.url, runner=runner)

    if request.download_type == "movie":
        destination, output_template = movie_output_template(request, metadata)
        playlist_mode = "--no-playlist"
        display_name = destination.name
    else:
        destination, output_template, display_name = tv_output_template(request, metadata)
        playlist_mode = "--yes-playlist"

    destination.mkdir(parents=True, exist_ok=True)
    run_yt_dlp(
        download_args(
            output_template=output_template,
            playlist_mode=playlist_mode,
            url=request.url,
        ),
        runner=runner,
    )

    return DownloadResult(
        download_type=request.download_type,
        destination=destination,
        display_name=display_name,
    )
