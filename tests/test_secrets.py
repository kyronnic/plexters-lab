from types import SimpleNamespace

from plexter.secrets import (
    BitwardenSdkSecrets,
    build_secret_provider,
)


def test_bitwarden_sdk_secrets_syncs_once_and_filters_project(monkeypatch) -> None:
    calls: list[tuple[str, str]] = []

    def fake_load_bws_sdk_secrets(**kwargs):
        calls.append((kwargs["organization_id"], kwargs["project_id"]))
        return {"PLEX_TOKEN": "sdk-token"}

    monkeypatch.setattr(
        "plexter.secrets.load_bws_sdk_secrets",
        fake_load_bws_sdk_secrets,
    )
    provider = BitwardenSdkSecrets(
        access_token="token",
        organization_id="org-123",
        project_id="project-123",
    )

    assert provider.get("PLEX_TOKEN") == "sdk-token"
    assert provider.get("MISSING") is None
    assert calls == [("org-123", "project-123")]


def test_load_bws_sdk_secrets_filters_by_project(monkeypatch) -> None:
    from plexter.secrets import load_bws_sdk_secrets

    class FakeAuth:
        def login_access_token(self, access_token):
            assert access_token == "token"
            return SimpleNamespace(
                success=True,
                data=SimpleNamespace(authenticated=True),
            )

    class FakeSecrets:
        def sync(self, organization_id, last_synced_date):
            assert organization_id == "org-123"
            assert last_synced_date is None
            return SimpleNamespace(
                success=True,
                data=SimpleNamespace(
                    secrets=[
                        SimpleNamespace(
                            key="PLEX_TOKEN",
                            value="sdk-token",
                            project_id="project-123",
                        ),
                        SimpleNamespace(
                            key="POSTGRES_PASSWORD",
                            value="other-project",
                            project_id="project-456",
                        ),
                    ]
                ),
            )

    class FakeClient:
        def __init__(self, settings):
            self.settings = settings

        def auth(self):
            return FakeAuth()

        def secrets(self):
            return FakeSecrets()

    monkeypatch.setattr("bitwarden_sdk.BitwardenClient", FakeClient)

    secrets = load_bws_sdk_secrets(
        access_token="token",
        organization_id="org-123",
        project_id="project-123",
    )

    assert secrets == {"PLEX_TOKEN": "sdk-token"}


def test_build_secret_provider_auto_disabled_without_bws_context(monkeypatch) -> None:
    for name in (
        "PLEXTER_CONFIG_BACKEND",
        "BWS_ACCESS_TOKEN",
        "PLEXTER_BWS_PROJECT_ID",
        "BWS_PROJECT_ID",
        "PLEXTER_BWS_ORGANIZATION_ID",
        "BWS_ORGANIZATION_ID",
    ):
        monkeypatch.delenv(name, raising=False)

    assert build_secret_provider() is None


def test_build_secret_provider_auto_prefers_sdk_with_token_and_org(monkeypatch) -> None:
    monkeypatch.delenv("PLEXTER_CONFIG_BACKEND", raising=False)
    monkeypatch.setenv("BWS_ACCESS_TOKEN", "token")
    monkeypatch.setenv("PLEXTER_BWS_ORGANIZATION_ID", "org-123")
    monkeypatch.setenv("PLEXTER_BWS_PROJECT_ID", "project-123")

    provider = build_secret_provider()

    assert isinstance(provider, BitwardenSdkSecrets)
    assert provider.organization_id == "org-123"
    assert provider.project_id == "project-123"


def test_build_secret_provider_auto_disabled_with_incomplete_bws_context(
    monkeypatch,
) -> None:
    monkeypatch.delenv("PLEXTER_CONFIG_BACKEND", raising=False)
    monkeypatch.delenv("PLEXTER_BWS_ORGANIZATION_ID", raising=False)
    monkeypatch.delenv("BWS_ORGANIZATION_ID", raising=False)
    monkeypatch.setenv("BWS_ACCESS_TOKEN", "token")
    monkeypatch.setenv("PLEXTER_BWS_PROJECT_ID", "project-123")

    provider = build_secret_provider()

    assert provider is None


def test_build_secret_provider_strict_requires_token_and_org(monkeypatch) -> None:
    monkeypatch.setenv("PLEXTER_CONFIG_BACKEND", "bitwarden")
    monkeypatch.setenv("PLEXTER_BWS_STRICT", "true")
    monkeypatch.setenv("BWS_ACCESS_TOKEN", "token")
    monkeypatch.delenv("PLEXTER_BWS_ORGANIZATION_ID", raising=False)
    monkeypatch.delenv("BWS_ORGANIZATION_ID", raising=False)

    try:
        build_secret_provider()
    except RuntimeError as error:
        assert "BWS_ACCESS_TOKEN and BWS_ORGANIZATION_ID" in str(error)
    else:
        raise AssertionError("Expected RuntimeError")
