from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"

load_dotenv(ENV_PATH)


@dataclass(frozen=True)
class Settings:
    postgres_host: str = os.getenv("POSTGRES_HOST", "localhost")
    postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    postgres_db: str = os.getenv("POSTGRES_DB", "plexter")
    postgres_user: str = os.getenv("POSTGRES_USER", "plexter")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "")

    plex_base_url: str = os.getenv("PLEX_BASE_URL", "")
    plex_token: str = os.getenv("PLEX_TOKEN", "")

    discord_webhook_url: str = os.getenv("DISCORD_WEBHOOK_URL", "")


settings = Settings()