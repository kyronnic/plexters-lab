from plexter.discord_bot.commands import (
    format_libraries,
    format_show_search_results,
)


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
