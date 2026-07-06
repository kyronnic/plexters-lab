from plexter.config import load_settings


class FakeProvider:
    def __init__(self, values: dict[str, str]) -> None:
        self.values = values

    def get(self, name: str) -> str | None:
        return self.values.get(name)


def test_load_settings_prefers_secret_provider_over_env(monkeypatch) -> None:
    monkeypatch.setenv("PLEX_TOKEN", "env-token")
    provider = FakeProvider({"PLEX_TOKEN": "bws-token"})

    settings = load_settings(provider)

    assert settings.plex_token == "bws-token"


def test_load_settings_falls_back_to_env_when_secret_missing(monkeypatch) -> None:
    monkeypatch.setenv("PLEX_BASE_URL", "http://plex.env:32400")
    provider = FakeProvider({})

    settings = load_settings(provider)

    assert settings.plex_base_url == "http://plex.env:32400"


def test_load_settings_accepts_bws_values_for_all_runtime_config(monkeypatch) -> None:
    monkeypatch.delenv("POSTGRES_HOST", raising=False)
    provider = FakeProvider(
        {
            "POSTGRES_HOST": "postgres.internal",
            "POSTGRES_PORT": "15432",
            "POSTGRES_DB": "plexter_prod",
            "POSTGRES_USER": "plexter_app",
            "POSTGRES_PASSWORD": "db-password",
            "PLEX_BASE_URL": "http://plex.internal:32400",
            "PLEX_TOKEN": "plex-token",
            "DISCORD_WEBHOOK_URL": "https://discord.test/webhook",
            "DISCORD_BOT_TOKEN": "bot-token",
            "DISCORD_GUILD_ID": "12345",
            "QBIT_BASE_URL": "http://qbit.test:8080",
            "QBIT_USER": "qbit-user",
            "QBIT_PASSWORD": "qbit-password",
            "PROWLARR_API_KEY": "prowlarr-key",
            "RADARR_MAIN_API_KEY": "radarr-main-key",
            "SONARR_KIDS_API_KEY": "sonarr-kids-key",
            "YOUTUBE_LIBRARY_ROOT": "/media/youtube",
        }
    )

    settings = load_settings(provider)

    assert settings.postgres_host == "postgres.internal"
    assert settings.postgres_port == 15432
    assert settings.postgres_db == "plexter_prod"
    assert settings.postgres_user == "plexter_app"
    assert settings.postgres_password == "db-password"
    assert settings.plex_base_url == "http://plex.internal:32400"
    assert settings.plex_token == "plex-token"
    assert settings.discord_webhook_url == "https://discord.test/webhook"
    assert settings.discord_bot_token == "bot-token"
    assert settings.discord_guild_id == 12345
    assert settings.qbit_base_url == "http://qbit.test:8080"
    assert settings.qbit_user == "qbit-user"
    assert settings.qbit_password == "qbit-password"
    assert settings.prowlarr_base_url == "http://localhost:9696"
    assert settings.prowlarr_api_key == "prowlarr-key"
    assert settings.radarr_instances[0].name == "main"
    assert settings.radarr_instances[0].base_url == "http://localhost:7878"
    assert settings.radarr_instances[0].api_key == "radarr-main-key"
    assert settings.sonarr_instances[2].name == "kids"
    assert settings.sonarr_instances[2].base_url == "http://localhost:8991"
    assert settings.sonarr_instances[2].api_key == "sonarr-kids-key"
    assert settings.youtube_library_root == "/media/youtube"


def test_load_settings_leaves_values_empty_when_config_missing(monkeypatch) -> None:
    for name in (
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "PLEX_BASE_URL",
        "PLEX_TOKEN",
        "DISCORD_WEBHOOK_URL",
        "DISCORD_BOT_TOKEN",
        "DISCORD_GUILD_ID",
        "QBIT_BASE_URL",
        "QBIT_USER",
        "QBIT_PASSWORD",
        "PROWLARR_BASE_URL",
        "PROWLARR_API_KEY",
        "RADARR_MAIN_API_KEY",
        "SONARR_KIDS_API_KEY",
        "YOUTUBE_LIBRARY_ROOT",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = load_settings(FakeProvider({}))

    assert settings.postgres_host == ""
    assert settings.postgres_port is None
    assert settings.postgres_db == ""
    assert settings.postgres_user == ""
    assert settings.postgres_password == ""
    assert settings.plex_base_url == ""
    assert settings.plex_token == ""
    assert settings.discord_webhook_url == ""
    assert settings.discord_bot_token == ""
    assert settings.discord_guild_id is None
    assert settings.qbit_base_url == ""
    assert settings.qbit_user == ""
    assert settings.qbit_password == ""
    assert settings.prowlarr_base_url == "http://localhost:9696"
    assert settings.prowlarr_api_key == ""
    assert settings.radarr_instances[0].base_url == "http://localhost:7878"
    assert settings.radarr_instances[0].api_key == ""
    assert settings.sonarr_instances[2].base_url == "http://localhost:8991"
    assert settings.sonarr_instances[2].api_key == ""
    assert settings.youtube_library_root == "/mnt/media/Library/YouTube"
