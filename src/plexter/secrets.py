from __future__ import annotations

from dataclasses import dataclass
import os


class SecretProvider:
    def get(self, name: str) -> str | None:
        raise NotImplementedError


@dataclass
class BitwardenSdkSecrets(SecretProvider):
    access_token: str
    organization_id: str
    project_id: str | None = None
    strict: bool = False

    def __post_init__(self) -> None:
        self._secrets: dict[str, str] | None = None

    def get(self, name: str) -> str | None:
        secrets = self._load_secrets()
        value = secrets.get(name)
        if value is None or value == "":
            return None
        return value

    def _load_secrets(self) -> dict[str, str]:
        if self._secrets is not None:
            return self._secrets

        try:
            self._secrets = load_bws_sdk_secrets(
                access_token=self.access_token,
                organization_id=self.organization_id,
                project_id=self.project_id,
            )
        except Exception:
            if self.strict:
                raise
            self._secrets = {}

        return self._secrets


def load_bws_sdk_secrets(
    *,
    access_token: str,
    organization_id: str,
    project_id: str | None = None,
) -> dict[str, str]:
    from bitwarden_sdk import BitwardenClient, ClientSettings

    api_url = os.getenv("BWS_API_URL", "").strip() or None
    identity_url = os.getenv("BWS_IDENTITY_URL", "").strip() or None
    client = BitwardenClient(
        ClientSettings(api_url=api_url, identity_url=identity_url)
    )
    login = client.auth().login_access_token(access_token)
    if not login.success or login.data is None or not login.data.authenticated:
        raise RuntimeError("Bitwarden SDK authentication failed.")

    response = client.secrets().sync(organization_id, None)
    if not response.success or response.data is None:
        raise RuntimeError("Bitwarden SDK secret sync failed.")

    secrets: dict[str, str] = {}
    for item in response.data.secrets or []:
        if project_id and str(item.project_id) != project_id:
            continue
        secrets[item.key] = item.value

    return secrets


def build_secret_provider() -> SecretProvider | None:
    backend = os.getenv("PLEXTER_CONFIG_BACKEND", "auto").strip().lower()
    if backend in {"", "env", "dotenv", "none"}:
        return None
    if backend not in {"auto", "bitwarden", "bws", "bws-sdk", "bitwarden-sdk"}:
        return None

    access_token = os.getenv("BWS_ACCESS_TOKEN", "").strip()
    organization_id = (
        os.getenv("PLEXTER_BWS_ORGANIZATION_ID", "").strip()
        or os.getenv("BWS_ORGANIZATION_ID", "").strip()
        or None
    )
    project_id = (
        os.getenv("PLEXTER_BWS_PROJECT_ID", "").strip()
        or os.getenv("BWS_PROJECT_ID", "").strip()
        or None
    )
    has_bws_context = bool(
        access_token
        or organization_id
        or project_id
    )
    if backend == "auto" and not has_bws_context:
        return None

    strict = os.getenv("PLEXTER_BWS_STRICT", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    if access_token and organization_id:
        return BitwardenSdkSecrets(
            access_token=access_token,
            organization_id=organization_id,
            project_id=project_id,
            strict=strict,
        )

    if strict:
        raise RuntimeError("BWS_ACCESS_TOKEN and BWS_ORGANIZATION_ID are required.")

    return None
