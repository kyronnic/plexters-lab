from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from typing import Any, Protocol, TextIO

from plexter.db import log_script_run
from plexter.notifications import notify_failure, notify_success
from plexter.playlists.round_robin import (
    PlexShowClient,
    RoundRobinPreview,
    build_round_robin_preview,
    format_episode_line,
)
from plexter.plex.client import PlexClient


ClientFactory = Callable[[], PlexShowClient]


class ScriptRunLogger(Protocol):
    def __call__(
        self,
        script_name: str,
        status: str,
        message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        pass


class RoundRobinNotifier(Protocol):
    def __call__(
        self,
        message: str,
        metadata: dict[str, Any] | None = None,
        *,
        title: str | None = None,
        description: str | None = None,
        color: int | None = None,
        fields: Sequence[dict[str, Any]] | None = None,
    ) -> int:
        pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="plexter-round-robin",
        description="Build and create round-robin Plex episode playlists.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_common_arguments(
        subparsers.add_parser(
            "preview",
            help="Preview a round-robin episode order.",
        )
    )
    add_common_arguments(
        subparsers.add_parser(
            "keys",
            help="Print only the ordered episode rating keys.",
        )
    )

    create_parser = subparsers.add_parser(
        "create",
        help="Create a Plex playlist from a round-robin episode order.",
    )
    add_common_arguments(create_parser)
    create_parser.add_argument(
        "--title",
        required=True,
        help="Plex playlist title to create.",
    )

    return parser


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "shows",
        nargs="+",
        help="Show search terms to include in the round-robin order.",
    )
    parser.add_argument(
        "--library",
        help="Optional Plex TV library title to filter search results.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Optional maximum number of episodes to include.",
    )
    parser.add_argument(
        "--preview-count",
        type=int,
        default=50,
        help="Number of ordered episodes to print.",
    )


def main(argv: Sequence[str] | None = None) -> None:
    raise SystemExit(run(argv))


def run(
    argv: Sequence[str] | None = None,
    client_factory: ClientFactory = PlexClient,
    output: TextIO | None = None,
    script_run_logger: ScriptRunLogger = log_script_run,
    success_notifier: RoundRobinNotifier = notify_success,
    failure_notifier: RoundRobinNotifier = notify_failure,
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    stream = output
    playlist_name = args.title if args.command == "create" else None
    dry_run = args.command != "create"

    client = client_factory()
    try:
        try:
            preview = build_round_robin_preview(
                client,
                args.shows,
                library_title=args.library,
                limit=args.limit,
            )
            if args.command == "create":
                client.create_video_playlist(args.title, preview.rating_keys)
            log_round_robin_success(
                script_run_logger,
                preview=preview,
                playlist_name=playlist_name,
                dry_run=dry_run,
            )
            notify_round_robin_success(
                success_notifier,
                preview=preview,
                playlist_name=playlist_name,
                dry_run=dry_run,
                output=stream,
            )
        except ValueError as exc:
            log_round_robin_failure(
                script_run_logger,
                error_message=str(exc),
                selected_shows=args.shows,
                playlist_name=playlist_name,
            )
            notify_round_robin_failure(
                failure_notifier,
                error_message=str(exc),
                selected_shows=args.shows,
                playlist_name=playlist_name,
                output=stream,
            )
            parser.exit(1, f"error: {exc}\n")
        except Exception as exc:
            log_round_robin_failure(
                script_run_logger,
                error_message=str(exc),
                selected_shows=args.shows,
                playlist_name=playlist_name,
            )
            notify_round_robin_failure(
                failure_notifier,
                error_message=str(exc),
                selected_shows=args.shows,
                playlist_name=playlist_name,
                output=stream,
            )
            raise
    finally:
        close = getattr(client, "close", None)
        if close:
            close()

    if args.command == "keys":
        _print(",".join(preview.rating_keys), stream)
        return 0

    if args.command == "create":
        _print(f"Created playlist: {args.title}", stream)

    print_round_robin_preview(preview, preview_count=args.preview_count, output=stream)
    return 0


def log_round_robin_success(
    script_run_logger: ScriptRunLogger,
    preview: RoundRobinPreview,
    playlist_name: str | None,
    dry_run: bool,
) -> int:
    episode_count = len(preview.episodes)
    selected_shows = [show.title for show in preview.shows]
    playlist_label = playlist_name or "dry run"

    return script_run_logger(
        script_name="round_robin",
        status="success",
        message=(
            f"Round robin playlist '{playlist_label}' completed "
            f"with {episode_count} episodes."
        ),
        metadata={
            "playlist_name": playlist_name,
            "selected_shows": selected_shows,
            "episode_count": episode_count,
            "dry_run": dry_run,
        },
    )


def log_round_robin_failure(
    script_run_logger: ScriptRunLogger,
    error_message: str,
    selected_shows: Sequence[str],
    playlist_name: str | None,
) -> int:
    return script_run_logger(
        script_name="round_robin",
        status="failure",
        message=error_message,
        metadata={
            "playlist_name": playlist_name,
            "selected_shows": list(selected_shows),
        },
    )


def notify_round_robin_success(
    notifier: RoundRobinNotifier,
    preview: RoundRobinPreview,
    playlist_name: str | None,
    dry_run: bool,
    output: TextIO | None = None,
) -> int | None:
    episode_count = len(preview.episodes)
    selected_shows = [show.title for show in preview.shows]
    playlist_label = playlist_name or "dry run"
    metadata = {
        "playlist_name": playlist_name,
        "selected_shows": selected_shows,
        "episode_count": episode_count,
        "dry_run": dry_run,
    }

    try:
        return notifier(
            f"Round robin playlist '{playlist_label}' completed with {episode_count} episodes.",
            metadata=metadata,
            title="Round Robin Complete",
            description=playlist_label,
            color=0x2ECC71,
            fields=[
                {"name": "Playlist", "value": playlist_label, "inline": True},
                {"name": "Episodes", "value": episode_count, "inline": True},
                {"name": "Dry Run", "value": dry_run, "inline": True},
                {"name": "Shows", "value": ", ".join(selected_shows) or "None"},
            ],
        )
    except Exception as exc:
        _print(f"warning: failed to send Discord notification: {exc}", output)
        return None


def notify_round_robin_failure(
    notifier: RoundRobinNotifier,
    error_message: str,
    selected_shows: Sequence[str],
    playlist_name: str | None,
    output: TextIO | None = None,
) -> int | None:
    playlist_label = playlist_name or "dry run"
    metadata = {
        "playlist_name": playlist_name,
        "selected_shows": list(selected_shows),
    }

    try:
        return notifier(
            error_message,
            metadata=metadata,
            title="Round Robin Failed",
            description=playlist_label,
            color=0xE74C3C,
            fields=[
                {"name": "Playlist", "value": playlist_label, "inline": True},
                {"name": "Shows", "value": ", ".join(selected_shows) or "None"},
                {"name": "Error", "value": error_message},
            ],
        )
    except Exception as exc:
        _print(f"warning: failed to send Discord notification: {exc}", output)
        return None


def print_round_robin_preview(
    preview: RoundRobinPreview,
    preview_count: int,
    output: TextIO | None = None,
) -> None:
    _print("Selected shows:", output)
    for show in preview.shows:
        _print(
            f"- {show.title} ratingKey={show.rating_key} episodes={len(show.episodes)}",
            output,
        )

    _print(f"\nRound-robin episodes: {len(preview.episodes)}", output)
    for episode in preview.episodes[:preview_count]:
        _print(f"- {format_episode_line(episode)}", output)

    remaining_count = len(preview.episodes) - preview_count
    if remaining_count > 0:
        _print(f"... {remaining_count} more episodes", output)

    _print("\nRating keys:", output)
    _print(",".join(preview.rating_keys), output)


def _print(message: str, output: TextIO | None = None) -> None:
    print(message, file=output)
