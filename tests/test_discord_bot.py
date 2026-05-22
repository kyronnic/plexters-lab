from types import SimpleNamespace

import pytest

from plexter.discord_bot.bot import create_bot


def test_create_bot_disables_message_content_intent() -> None:
    bot = create_bot(guild_id=123)

    assert bot.intents.message_content is False


def test_create_bot_requires_guild_id(monkeypatch) -> None:
    monkeypatch.setattr(
        "plexter.discord_bot.bot.settings",
        SimpleNamespace(discord_guild_id=None),
    )

    with pytest.raises(ValueError, match="DISCORD_GUILD_ID"):
        create_bot(guild_id=None)
