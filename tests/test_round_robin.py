import pytest

from plexter.playlists.round_robin import (
    RoundRobinEpisode,
    RoundRobinShow,
    create_round_robin_playlist,
    build_search_queries,
    build_round_robin_preview,
    build_round_robin_episode_order,
    build_round_robin_playlist,
    find_best_show_match,
    find_library_show_candidates,
    format_episode_line,
    get_rating_keys,
)


class FakePlexShowClient:
    def __init__(self) -> None:
        self.shows = {
            "frieren": [
                {"title": "Frieren: Beyond Journey's End", "ratingKey": "show-a"},
                {"title": "Frieren", "ratingKey": "show-exact"},
            ],
            "delicious in dungeon": [],
            "delicious": [
                {"title": "Delicious in Dungeon", "ratingKey": "show-b"},
            ],
        }
        self.episodes = {
            "show-exact": [
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
        self.library_shows = [
            {"title": "Delicious in Dungeon", "ratingKey": "show-b"},
        ]
        self.created_playlists: list[tuple[str, list[str | int]]] = []

    def search_shows(
        self,
        query: str,
        library_title: str | None = None,
    ) -> list[dict]:
        return self.shows.get(query.casefold(), [])

    def get_show_episodes(self, show_rating_key: str | int) -> list[dict]:
        return self.episodes[str(show_rating_key)]

    def get_shows(self, library_title: str | None = None) -> list[dict]:
        return self.library_shows

    def create_video_playlist(
        self,
        title: str,
        episode_rating_keys: list[str | int],
    ) -> dict:
        self.created_playlists.append((title, episode_rating_keys))
        return {}


def episode(rating_key: str, title: str | None = None) -> RoundRobinEpisode:
    return RoundRobinEpisode(
        rating_key=rating_key,
        title=title or rating_key,
    )


def test_build_round_robin_episode_order_interleaves_even_lists() -> None:
    ordered = build_round_robin_episode_order(
        [
            ["a1", "a2", "a3"],
            ["b1", "b2", "b3"],
            ["c1", "c2", "c3"],
        ]
    )

    assert ordered == ["a1", "b1", "c1", "a2", "b2", "c2", "a3", "b3", "c3"]


def test_build_round_robin_episode_order_skips_exhausted_lists() -> None:
    ordered = build_round_robin_episode_order(
        [
            ["a1", "a2", "a3"],
            [],
            ["c1"],
            ["d1", "d2"],
        ]
    )

    assert ordered == ["a1", "c1", "d1", "a2", "d2", "a3"]


def test_build_round_robin_episode_order_applies_limit() -> None:
    ordered = build_round_robin_episode_order(
        [
            ["a1", "a2", "a3"],
            ["b1", "b2", "b3"],
        ],
        limit=4,
    )

    assert ordered == ["a1", "b1", "a2", "b2"]


def test_build_round_robin_episode_order_allows_zero_limit() -> None:
    ordered = build_round_robin_episode_order([["a1"], ["b1"]], limit=0)

    assert ordered == []


def test_build_round_robin_episode_order_rejects_negative_limit() -> None:
    with pytest.raises(ValueError, match="limit"):
        build_round_robin_episode_order([["a1"]], limit=-1)


def test_build_round_robin_playlist_returns_episode_objects() -> None:
    shows = [
        RoundRobinShow(
            title="Show A",
            episodes=[episode("a1"), episode("a2")],
        ),
        RoundRobinShow(
            title="Show B",
            episodes=[episode("b1")],
        ),
    ]

    ordered = build_round_robin_playlist(shows)

    assert get_rating_keys(ordered) == ["a1", "b1", "a2"]


def test_round_robin_show_from_plex_show_converts_metadata() -> None:
    show = {"title": "Frieren", "ratingKey": 123}
    episodes = [
        {
            "ratingKey": 456,
            "title": "The Journey's End",
            "parentIndex": "1",
            "index": "1",
        }
    ]

    round_robin_show = RoundRobinShow.from_plex_show(show, episodes)

    assert round_robin_show.title == "Frieren"
    assert round_robin_show.rating_key == "123"
    assert get_rating_keys(round_robin_show.episodes) == ["456"]
    assert round_robin_show.episodes[0].season_number == 1
    assert round_robin_show.episodes[0].episode_number == 1


def test_find_best_show_match_prefers_exact_title_match() -> None:
    selected = find_best_show_match(
        [
            {"title": "Frieren: Beyond Journey's End", "ratingKey": "show-a"},
            {"title": "Frieren", "ratingKey": "show-b"},
        ],
        "frieren",
    )

    assert selected == {"title": "Frieren", "ratingKey": "show-b"}


def test_build_search_queries_uses_full_query_then_meaningful_words() -> None:
    assert build_search_queries("Delicious in Dungeon") == [
        "Delicious in Dungeon",
        "Delicious",
        "Dungeon",
    ]


def test_find_library_show_candidates_falls_back_to_library_titles() -> None:
    candidates = find_library_show_candidates(
        [
            {"title": "Frieren: Beyond Journey's End", "ratingKey": "show-a"},
            {"title": "Delicious in Dungeon", "ratingKey": "show-b"},
        ],
        "Delicious in Dungeon",
    )

    assert candidates == [{"title": "Delicious in Dungeon", "ratingKey": "show-b"}]


def test_build_round_robin_preview_fetches_shows_and_interleaves_episodes() -> None:
    preview = build_round_robin_preview(
        FakePlexShowClient(),
        ["Frieren", "Delicious in Dungeon"],
    )

    assert [show.title for show in preview.shows] == [
        "Frieren",
        "Delicious in Dungeon",
    ]
    assert preview.rating_keys == ["a1", "b1", "a2"]


def test_create_round_robin_playlist_creates_from_preview_rating_keys() -> None:
    client = FakePlexShowClient()

    preview = create_round_robin_playlist(
        client,
        "Anime Round Robin",
        ["Frieren", "Delicious in Dungeon"],
    )

    assert preview.rating_keys == ["a1", "b1", "a2"]
    assert client.created_playlists == [
        ("Anime Round Robin", ["a1", "b1", "a2"]),
    ]


def test_format_episode_line_includes_show_episode_and_rating_key() -> None:
    line = format_episode_line(
        RoundRobinEpisode(
            rating_key="abc",
            title="The Journey's End",
            show_title="Frieren",
            season_number=1,
            episode_number=1,
        )
    )

    assert line == "Frieren - S01E01 - The Journey's End ratingKey=abc"
