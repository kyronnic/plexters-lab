from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import discord
from discord import app_commands

from plexter.plex.client import PlexClient


MAX_SEARCH_RESULTS = 5


def register_commands(
    tree: app_commands.CommandTree,
    guild: discord.Object,
) -> None:
    @tree.command(
        name="ping",
        description="Check whether Plexter is online.",
        guild=guild,
    )
    async def ping(interaction: discord.Interaction) -> None:
        await interaction.response.send_message("Plexter is online.")

    @tree.command(
        name="libraries",
        description="List Plex libraries.",
        guild=guild,
    )
    async def libraries(interaction: discord.Interaction) -> None:
        try:
            with_plex_client = PlexClient()
            try:
                message = format_libraries(with_plex_client.get_libraries())
            finally:
                with_plex_client.close()
        except Exception as exc:
            message = f"Could not load Plex libraries: {exc}"

        await interaction.response.send_message(message)

    @tree.command(
        name="search",
        description="Search Plex TV shows.",
        guild=guild,
    )
    @app_commands.describe(query="Show title to search for.")
    async def search(interaction: discord.Interaction, query: str) -> None:
        try:
            with_plex_client = PlexClient()
            try:
                message = format_show_search_results(
                    query,
                    with_plex_client.search_shows(query)[:MAX_SEARCH_RESULTS],
                )
            finally:
                with_plex_client.close()
        except Exception as exc:
            message = f"Search failed: {exc}"

        await interaction.response.send_message(message)


def format_libraries(libraries: Sequence[dict[str, Any]]) -> str:
    if not libraries:
        return "No Plex libraries found."

    lines = [
        f"- {library.get('title', 'Untitled')} ({library.get('type', 'unknown')})"
        for library in libraries[:10]
    ]
    if len(libraries) > 10:
        lines.append(f"...and {len(libraries) - 10} more.")

    return "\n".join(lines)


def format_show_search_results(
    query: str,
    shows: Sequence[dict[str, Any]],
) -> str:
    if not shows:
        return f"No shows found for '{query}'."

    lines = [
        f"- {show.get('title', 'Untitled')}"
        for show in shows[:MAX_SEARCH_RESULTS]
    ]

    return "\n".join(lines)
