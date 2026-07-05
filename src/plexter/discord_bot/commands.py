from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import discord
from discord import app_commands

from plexter.plex.client import PlexClient
from plexter.services.activity import get_recent_activity
from plexter.services.health import SystemStatus, get_system_status
from plexter.services.torrents import get_stalled_torrents, format_stalled_torrents_message


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

    @tree.command(
        name="status",
        description="Show Plexter system status.",
        guild=guild,
    )
    async def status(interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            format_system_status(get_system_status())
        )

    @tree.command(
        name="recent",
        description="Show recent Plexter activity.",
        guild=guild,
    )
    async def recent(interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            format_recent_activity(get_recent_activity(limit=5))
        )

    @tree.command(
        name="stalled",
        description="Show stalled or inactive torrents from qBittorrent.",
        guild=guild,
    )
    @app_commands.describe(
        hours="Hours threshold for inactivity (default: 48)",
    )
    async def stalled(
        interaction: discord.Interaction,
        hours: int | None = None,
    ) -> None:
        try:
            threshold_hours = hours or 48
            torrents = get_stalled_torrents(hours_inactive=threshold_hours)
            message = format_stalled_torrents_message(torrents)
        except Exception as exc:
            message = f"Failed to fetch stalled torrents: {exc}"

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


def format_system_status(status: SystemStatus) -> str:
    plex_status = "Connected" if status.plex.connected else "Failed"
    postgres_status = "Connected" if status.postgres.connected else "Failed"

    return "\n".join(
        [
            "Atlas: Online",
            f"Plex: {plex_status}",
            f"Postgres: {postgres_status}",
            f"Libraries: {status.library_count}",
        ]
    )


def format_recent_activity(activities: Sequence[dict[str, Any]]) -> str:
    if not activities:
        return "No recent Plexter activity."

    lines = [
        f"- {activity.get('summary', 'Activity recorded')}"
        for activity in activities[:5]
    ]

    return "\n".join(lines)
