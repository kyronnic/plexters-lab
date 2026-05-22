from __future__ import annotations

import discord
from discord import app_commands

from plexter.config import settings
from plexter.discord_bot.commands import register_commands


class PlexterDiscordBot(discord.Client):
    def __init__(self, guild_id: int) -> None:
        intents = discord.Intents.default()
        intents.message_content = False

        super().__init__(intents=intents)
        self.guild = discord.Object(id=guild_id)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self) -> None:
        register_commands(self.tree, self.guild)
        await self.tree.sync(guild=self.guild)


def create_bot(guild_id: int | None = None) -> PlexterDiscordBot:
    resolved_guild_id = guild_id or settings.discord_guild_id
    if resolved_guild_id is None:
        raise ValueError("DISCORD_GUILD_ID is not set.")

    return PlexterDiscordBot(guild_id=resolved_guild_id)


def run_bot() -> None:
    if not settings.discord_bot_token:
        raise ValueError("DISCORD_BOT_TOKEN is not set.")

    bot = create_bot()
    bot.run(settings.discord_bot_token)
