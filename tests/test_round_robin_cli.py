from io import StringIO

from plexter.playlists.round_robin.cli import run


class FakeCliPlexClient:
    def __init__(self) -> None:
        self.closed = False
        self.created_playlists: list[tuple[str, list[str | int]]] = []

    def search_shows(
        self,
        query: str,
        library_title: str | None = None,
    ) -> list[dict]:
        shows = {
            "frieren": [{"title": "Frieren", "ratingKey": "show-a"}],
            "apothecary diaries": [
                {"title": "The Apothecary Diaries", "ratingKey": "show-b"}
            ],
        }
        return shows.get(query.casefold(), [])

    def get_show_episodes(self, show_rating_key: str | int) -> list[dict]:
        episodes = {
            "show-a": [
                {
                    "ratingKey": "a1",
                    "title": "A1",
                    "parentIndex": 1,
                    "index": 1,
                },
                {
                    "ratingKey": "a2",
                    "title": "A2",
                    "parentIndex": 1,
                    "index": 2,
                },
            ],
            "show-b": [
                {
                    "ratingKey": "b1",
                    "title": "B1",
                    "parentIndex": 1,
                    "index": 1,
                },
            ],
        }
        return episodes[str(show_rating_key)]

    def get_shows(self, library_title: str | None = None) -> list[dict]:
        return []

    def create_video_playlist(
        self,
        title: str,
        episode_rating_keys: list[str | int],
    ) -> dict:
        self.created_playlists.append((title, episode_rating_keys))
        return {}

    def close(self) -> None:
        self.closed = True


class FakeScriptRunLogger:
    def __init__(self) -> None:
        self.entries: list[dict] = []

    def __call__(
        self,
        script_name: str,
        status: str,
        message: str | None = None,
        metadata: dict | None = None,
    ) -> int:
        self.entries.append(
            {
                "script_name": script_name,
                "status": status,
                "message": message,
                "metadata": metadata,
            }
        )
        return len(self.entries)


def test_round_robin_cli_preview_prints_episode_preview() -> None:
    output = StringIO()
    logger = FakeScriptRunLogger()

    exit_code = run(
        ["preview", "Frieren", "Apothecary Diaries", "--preview-count", "2"],
        client_factory=FakeCliPlexClient,
        output=output,
        script_run_logger=logger,
    )

    assert exit_code == 0
    text = output.getvalue()
    assert "Selected shows:" in text
    assert "- Frieren - S01E01 - A1 ratingKey=a1" in text
    assert "- The Apothecary Diaries - S01E01 - B1 ratingKey=b1" in text
    assert "... 1 more episodes" in text
    assert logger.entries == [
        {
            "script_name": "round_robin",
            "status": "success",
            "message": "Round robin playlist 'dry run' completed with 3 episodes.",
            "metadata": {
                "playlist_name": None,
                "selected_shows": ["Frieren", "The Apothecary Diaries"],
                "episode_count": 3,
                "dry_run": True,
            },
        }
    ]


def test_round_robin_cli_keys_prints_only_rating_keys() -> None:
    output = StringIO()
    logger = FakeScriptRunLogger()

    exit_code = run(
        ["keys", "Frieren", "Apothecary Diaries"],
        client_factory=FakeCliPlexClient,
        output=output,
        script_run_logger=logger,
    )

    assert exit_code == 0
    assert output.getvalue() == "a1,b1,a2\n"
    assert logger.entries[0]["status"] == "success"
    assert logger.entries[0]["metadata"]["dry_run"] is True


def test_round_robin_cli_create_creates_playlist_and_prints_preview() -> None:
    output = StringIO()
    logger = FakeScriptRunLogger()
    clients: list[FakeCliPlexClient] = []

    def client_factory() -> FakeCliPlexClient:
        client = FakeCliPlexClient()
        clients.append(client)
        return client

    exit_code = run(
        [
            "create",
            "Frieren",
            "Apothecary Diaries",
            "--title",
            "Anime Round Robin",
        ],
        client_factory=client_factory,
        output=output,
        script_run_logger=logger,
    )

    assert exit_code == 0
    assert clients[0].created_playlists == [
        ("Anime Round Robin", ["a1", "b1", "a2"]),
    ]
    assert clients[0].closed is True
    assert "Created playlist: Anime Round Robin" in output.getvalue()
    assert logger.entries == [
        {
            "script_name": "round_robin",
            "status": "success",
            "message": (
                "Round robin playlist 'Anime Round Robin' completed "
                "with 3 episodes."
            ),
            "metadata": {
                "playlist_name": "Anime Round Robin",
                "selected_shows": ["Frieren", "The Apothecary Diaries"],
                "episode_count": 3,
                "dry_run": False,
            },
        }
    ]


def test_round_robin_cli_logs_failure() -> None:
    output = StringIO()
    logger = FakeScriptRunLogger()

    try:
        run(
            ["create", "Missing Show", "--title", "Anime Round Robin"],
            client_factory=FakeCliPlexClient,
            output=output,
            script_run_logger=logger,
        )
    except SystemExit as exc:
        assert exc.code == 1
    else:
        raise AssertionError("Expected SystemExit.")

    assert logger.entries == [
        {
            "script_name": "round_robin",
            "status": "failure",
            "message": (
                "No show found for query: Missing Show. "
                "Tried Plex search terms: Missing Show, Missing, Show."
            ),
            "metadata": {
                "playlist_name": "Anime Round Robin",
                "selected_shows": ["Missing Show"],
            },
        }
    ]
