from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv

from plexter.secrets import SecretProvider, build_secret_provider


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"

load_dotenv(ENV_PATH)


def optional_int_value(value: str | None) -> int | None:
    value = (value or "").strip()
    if not value:
        return None

    try:
        return int(value)
    except ValueError:
        return None


def config_value(
    name: str,
    *,
    provider: SecretProvider | None = None,
) -> str:
    if provider is not None:
        secret = provider.get(name)
        if secret is not None:
            return secret

    return os.getenv(name, "")


def optional_int_config(
    name: str,
    *,
    provider: SecretProvider | None = None,
) -> int | None:
    return optional_int_value(config_value(name, provider=provider))


@dataclass(frozen=True)
class Settings:
    postgres_host: str
    postgres_port: int | None
    postgres_db: str
    postgres_user: str
    postgres_password: str

    plex_base_url: str
    plex_token: str

    discord_webhook_url: str
    discord_bot_token: str
    discord_guild_id: int | None


def load_settings(provider: SecretProvider | None = None) -> Settings:
    if provider is None:
        provider = build_secret_provider()

    return Settings(
        postgres_host=config_value("POSTGRES_HOST", provider=provider),
        postgres_port=optional_int_config("POSTGRES_PORT", provider=provider),
        postgres_db=config_value("POSTGRES_DB", provider=provider),
        postgres_user=config_value("POSTGRES_USER", provider=provider),
        postgres_password=config_value("POSTGRES_PASSWORD", provider=provider),
        plex_base_url=config_value("PLEX_BASE_URL", provider=provider),
        plex_token=config_value("PLEX_TOKEN", provider=provider),
        discord_webhook_url=config_value("DISCORD_WEBHOOK_URL", provider=provider),
        discord_bot_token=config_value("DISCORD_BOT_TOKEN", provider=provider),
        discord_guild_id=optional_int_value(
            config_value("DISCORD_GUILD_ID", provider=provider)
        ),
    )


settings = load_settings()
