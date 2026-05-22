import argparse

from plexter.playlists.round_robin.cli import run


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preview or create a round-robin Plex episode playlist.",
    )
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
    parser.add_argument(
        "--keys-only",
        action="store_true",
        help="Print only the ordered Plex rating keys.",
    )
    parser.add_argument(
        "--create-playlist",
        metavar="TITLE",
        help="Create a Plex video playlist with this title after building the preview.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    command = "keys" if args.keys_only else "preview"
    argv = [command, *args.shows]

    if args.library:
        argv.extend(["--library", args.library])
    if args.limit is not None:
        argv.extend(["--limit", str(args.limit)])
    if args.preview_count is not None:
        argv.extend(["--preview-count", str(args.preview_count)])
    if args.create_playlist:
        argv[0] = "create"
        argv.extend(["--title", args.create_playlist])

    raise SystemExit(run(argv))


if __name__ == "__main__":
    main()
