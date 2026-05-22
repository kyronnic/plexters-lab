from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol, TypeVar


T = TypeVar("T")


class PlexShowClient(Protocol):
    def search_shows(
        self,
        query: str,
        library_title: str | None = None,
    ) -> list[dict[str, Any]]:
        pass

    def get_show_episodes(self, show_rating_key: str | int) -> list[dict[str, Any]]:
        pass

    def get_shows(self, library_title: str | None = None) -> list[dict[str, Any]]:
        pass

    def create_video_playlist(
        self,
        title: str,
        episode_rating_keys: Sequence[str | int],
    ) -> dict[str, Any]:
        pass


@dataclass(frozen=True)
class RoundRobinEpisode:
    rating_key: str
    title: str
    show_title: str | None = None
    season_number: int | None = None
    episode_number: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_plex_metadata(
        cls,
        metadata: dict[str, Any],
        show_title: str | None = None,
    ) -> RoundRobinEpisode:
        rating_key = metadata.get("ratingKey")
        if rating_key is None:
            raise ValueError("Episode metadata is missing ratingKey.")

        return cls(
            rating_key=str(rating_key),
            title=str(metadata.get("title") or ""),
            show_title=show_title or metadata.get("grandparentTitle"),
            season_number=_optional_int(metadata.get("parentIndex")),
            episode_number=_optional_int(metadata.get("index")),
            metadata=metadata,
        )


@dataclass(frozen=True)
class RoundRobinShow:
    title: str
    episodes: Sequence[RoundRobinEpisode]
    rating_key: str | None = None

    @classmethod
    def from_plex_show(
        cls,
        show: dict[str, Any],
        episodes: Sequence[dict[str, Any]],
    ) -> RoundRobinShow:
        title = str(show.get("title") or "")
        rating_key = show.get("ratingKey")

        return cls(
            title=title,
            rating_key=str(rating_key) if rating_key is not None else None,
            episodes=[
                RoundRobinEpisode.from_plex_metadata(episode, show_title=title)
                for episode in episodes
            ],
        )


@dataclass(frozen=True)
class RoundRobinPreview:
    shows: Sequence[RoundRobinShow]
    episodes: Sequence[RoundRobinEpisode]

    @property
    def rating_keys(self) -> list[str]:
        return get_rating_keys(self.episodes)


def build_round_robin_preview(
    client: PlexShowClient,
    show_queries: Sequence[str],
    library_title: str | None = None,
    limit: int | None = None,
) -> RoundRobinPreview:
    if not show_queries:
        raise ValueError("At least one show query is required.")

    shows = [
        fetch_round_robin_show(client, query, library_title=library_title)
        for query in show_queries
    ]
    episodes = build_round_robin_playlist(shows, limit=limit)

    return RoundRobinPreview(
        shows=shows,
        episodes=episodes,
    )


def create_round_robin_playlist(
    client: PlexShowClient,
    title: str,
    show_queries: Sequence[str],
    library_title: str | None = None,
    limit: int | None = None,
) -> RoundRobinPreview:
    preview = build_round_robin_preview(
        client,
        show_queries,
        library_title=library_title,
        limit=limit,
    )
    client.create_video_playlist(title, preview.rating_keys)

    return preview


def fetch_round_robin_show(
    client: PlexShowClient,
    query: str,
    library_title: str | None = None,
) -> RoundRobinShow:
    clean_query = query.strip()
    if not clean_query:
        raise ValueError("Show query cannot be blank.")

    show = find_best_show_match(
        search_show_candidates(client, clean_query, library_title=library_title),
        clean_query,
    )
    if show is None:
        search_queries = ", ".join(build_search_queries(clean_query))
        raise ValueError(
            f"No show found for query: {clean_query}. "
            f"Tried Plex search terms: {search_queries}."
        )

    rating_key = show.get("ratingKey")
    if rating_key is None:
        raise ValueError(f"Show is missing ratingKey: {show.get('title') or clean_query}")

    episodes = client.get_show_episodes(rating_key)
    return RoundRobinShow.from_plex_show(show, episodes)


def search_show_candidates(
    client: PlexShowClient,
    query: str,
    library_title: str | None = None,
) -> list[dict[str, Any]]:
    candidates_by_key: dict[str, dict[str, Any]] = {}

    for search_query in build_search_queries(query):
        for show in client.search_shows(search_query, library_title=library_title):
            candidate_key = str(show.get("ratingKey") or show.get("key") or id(show))
            candidates_by_key[candidate_key] = show

        if candidates_by_key:
            return list(candidates_by_key.values())

    return find_library_show_candidates(
        client.get_shows(library_title=library_title),
        query,
    )


def find_library_show_candidates(
    shows: Sequence[dict[str, Any]],
    query: str,
) -> list[dict[str, Any]]:
    normalized_query = _normalize_title(query)
    exact_matches = [
        show
        for show in shows
        if _normalize_title(show.get("title")) == normalized_query
    ]
    if exact_matches:
        return exact_matches

    query_words = set(build_search_queries(query)[1:])
    return [
        show
        for show in shows
        if normalized_query in _normalize_title(show.get("title"))
        or any(
            _normalize_title(query_word) in _normalize_title(show.get("title"))
            for query_word in query_words
        )
    ]


def build_search_queries(query: str) -> list[str]:
    clean_query = query.strip()
    if not clean_query:
        return []

    queries = [clean_query]
    words = [
        word
        for word in clean_query.replace(":", " ").split()
        if word.casefold() not in {"a", "an", "and", "in", "of", "the"}
    ]

    queries.extend(words)

    return _dedupe_preserving_order(queries)


def find_best_show_match(
    shows: Sequence[dict[str, Any]],
    query: str,
) -> dict[str, Any] | None:
    if not shows:
        return None

    normalized_query = _normalize_title(query)
    for show in shows:
        if _normalize_title(show.get("title")) == normalized_query:
            return show

    return shows[0]


def build_round_robin_episode_order(
    episode_lists: Sequence[Sequence[T]],
    limit: int | None = None,
) -> list[T]:
    if limit is not None and limit < 0:
        raise ValueError("limit must be greater than or equal to 0.")
    if limit == 0:
        return []

    ordered: list[T] = []
    max_episode_count = max((len(episodes) for episodes in episode_lists), default=0)

    for episode_index in range(max_episode_count):
        for episodes in episode_lists:
            if episode_index >= len(episodes):
                continue

            ordered.append(episodes[episode_index])
            if limit is not None and len(ordered) >= limit:
                return ordered

    return ordered


def build_round_robin_playlist(
    shows: Sequence[RoundRobinShow],
    limit: int | None = None,
) -> list[RoundRobinEpisode]:
    return build_round_robin_episode_order(
        [show.episodes for show in shows],
        limit=limit,
    )


def get_rating_keys(episodes: Sequence[RoundRobinEpisode]) -> list[str]:
    return [episode.rating_key for episode in episodes]


def format_episode_line(episode: RoundRobinEpisode) -> str:
    episode_code = format_episode_code(
        episode.season_number,
        episode.episode_number,
    )
    title_parts = [
        part
        for part in (episode.show_title, episode_code, episode.title)
        if part
    ]

    return f"{' - '.join(title_parts)} ratingKey={episode.rating_key}"


def format_episode_code(
    season_number: int | None,
    episode_number: int | None,
) -> str | None:
    if season_number is None or episode_number is None:
        return None

    return f"S{season_number:02}E{episode_number:02}"


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None

    return int(value)


def _normalize_title(value: Any) -> str:
    return str(value or "").casefold().strip()


def _dedupe_preserving_order(values: Sequence[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()

    for value in values:
        normalized_value = value.casefold().strip()
        if not normalized_value or normalized_value in seen:
            continue

        seen.add(normalized_value)
        deduped.append(value)

    return deduped
