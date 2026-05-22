import base64
import hashlib
import json
import os
import platform
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import httpx
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

PLEX_BASE = "https://clients.plex.tv/api/v2/auth"

def _b64url(data: bytes) -> str:
    """Base64 URL encode without '=' padding"""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

def _b64url_decode(s: str) -> bytes:
    """Decode base64url string with missing padding"""
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)

@dataclass
class Keypair:
    private_bytes: bytes
    public_bytes: bytes

    @property
    def key_id(self) -> str:
        return hashlib.sha256(self.private_bytes + self.public_bytes).hexdigest()

    @property
    def private_jwk(self) -> jwt.PyJWK:
        return jwt.PyJWK.from_dict(
            {
                "kty": "OKP",
                "crv": "Ed25519",
                "x": _b64url(self.public_bytes),
                "d": _b64url(self.private_bytes),
                "use": "sig",
                "alg": "EdDSA",
                "kid": self.key_id
            }
        )

    @property
    def public_jwk(self) -> dict:
        return {
            "kty": "OKP",
            "crv": "Ed25519",
            "x": _b64url(self.public_bytes),
            "use": "sig",
            "alg": "EdDSA",
            "kid": self.key_id
        }

def _get_config_dir(config_dir: Optional[Path] = None) -> Path:
    """
    Priority:
    1) explicit config_dir argument
    2) PLEX_CONFIG_DIR env var
    3) ./config relative to current working directory
    """
    if config_dir is not None:
        cd = config_dir
    elif os.getenv("PLEX_CONFIG_DIR"):
        cd = Path(os.environ["PLEX_CONFIG_DIR"])
    else:
        cd = Path.cwd() / "config"

    cd.mkdir(parents=True, exist_ok=True)
    return cd

def _paths(config_dir: Optional[Path] = None) -> Tuple[Path, Path]:
    cd = _get_config_dir(config_dir)
    key_path = cd / "device_ed25519.key"
    token_path = cd / "plex_jwt_token.json"
    return key_path, token_path

def _require_env(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise RuntimeError(f"{name} not set in environment")
    return val

def _base_headers(client_id: str) -> dict:
    return {
        "X-Plex-Client-Identifier": client_id,
        "X-Plex-Product": "PlexLab",
        "X-Plex-Version": "0.1.0",
        "X-Plex-Device": "Plexlab Dev Client",
        "X-Plex-Platform": platform.system(),
        "X-Plex-Platform-Version": platform.release() or "0.0"
    }

# Keypair storage
def _save_keypair(key_path: Path, kp: Keypair) -> None:
    key_path.write_text(
        json.dumps(
            {
                "private": _b64url(kp.private_bytes),
                "public": _b64url(kp.public_bytes)
            },
            indent=2
        )
    )
    try:
        os.chmod(key_path, 0o600)
    except Exception:
        pass

def _load_keypair(key_path: Path) -> Optional[Keypair]:
    if not key_path.exists():
        return None
    try:
        raw = key_path.read_text().strip()
        if not raw:
            return None
        data = json.loads(raw)
        private_bytes = _b64url_decode(data["private"])
        public_bytes = _b64url_decode(data["public"])
        return Keypair(private_bytes=private_bytes, public_bytes=public_bytes)
    except Exception:
        return None

def _generate_keypair(key_path: Path) -> Keypair:
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )

    kp = Keypair(private_bytes=private_bytes, public_bytes=public_bytes)
    _save_keypair(key_path, kp)
    return kp

def _get_or_create_keypair(
        client_id: str,
        legacy_token: Optional[str],
        key_path: Path
) -> Keypair:
    kp = _load_keypair(key_path)
    if kp is not None:
        return kp

    if not legacy_token:
        raise RuntimeError(
            "No device key found and PLEX_TOKEN is not set in .env. "
            "You need a legacy Plex token once to register the device JWK"
        )

    kp = _generate_keypair(key_path)
    _register_device_jwk(client_id, legacy_token, kp)
    return kp

# JWK registration
def _register_device_jwk(client_id: str, legacy_token: str, kp: Keypair) -> None:
    """
    Register this device's public JWK with Plex using the legacy token.
    This only needs to happen once per client_id
    :param kp:
    :return:
    """
    headers = _base_headers(client_id)
    headers["X-Plex-Token"] = legacy_token
    body = {"jwk": kp.public_jwk}

    resp = httpx.post(f"{PLEX_BASE}/jwk", headers=headers, json=body, timeout=10)
    resp.raise_for_status()

# Token cache
def _load_cached_token(token_path: Path):
    if not token_path.exists():
        return None
    try:
        data = json.loads(token_path.read_text())
        return data["token"], int(data["expires_at"])
    except Exception:
        return None

def _save_token(token_path: Path, token: str, expires_at: int) -> None:
    token_path.write_text(
        json.dumps({"token": token, "expires_at": int(expires_at)}, indent=2)
    )

# JWT flow: nonce -> device JWT -> Plex token
def _get_nonce(client_id: str) -> str:
    resp = httpx.get(f"{PLEX_BASE}/nonce", headers=_base_headers(client_id), timeout=10)
    resp.raise_for_status()
    return resp.json()["nonce"]

def _build_device_jwt(client_id: str, kp: Keypair, nonce: str, scope: str) -> str:
    now = int(time.time())
    payload = {
        "nonce": nonce,
        "scope": scope,
        "aud": "plex.tv",
        "iss": client_id,
        "iat": now,
        "exp": now + 5 * 60 # 5 minutes
    }
    headers = {"kid": kp.key_id}

    return jwt.encode(
        payload=payload,
        key=kp.private_jwk,
        algorithm="EdDSA",
        headers=headers
    )

def _exchange_for_plex_token(client_id: str, device_jwt: str) -> str:
    body = {"jwt": device_jwt}
    resp = httpx.post(
        f"{PLEX_BASE}/token",
        headers=_base_headers(client_id),
        json=body,
        timeout=10
    )
    resp.raise_for_status()
    data = resp.json()
    token = (
        data.get("auth_token")
        or data.get("authToken")
        or data.get("token")
        or data.get("access_token")
    )
    if not token:
        raise RuntimeError(f"Could not find auth token in response keys: {list(data.keys())}")
    return token

# Public API
def get_plex_token(
        scope: str = "username,email,friendly_name",
        force_refresh: bool = False,
        config_dir: Optional[Path] = None
) -> str:
    """
    Return a valid Plex JWT auth token.
    - Uses cached token if still valid
    - Otherwis goes through nonce -> device JWT -> Plex JWT flow
    """
    client_id = _require_env("PLEX_CLIENT_ID")
    legacy_token = os.getenv("PLEX_LEGACY_TOKEN")

    key_path, token_path = _paths(config_dir)
    print("[JWT] key_path:", key_path)
    print("[JWT] token_path:", token_path)

    if not force_refresh:
        cached = _load_cached_token(token_path)
        if cached:
            token, exp = cached
            if exp > time.time() + 60:
                return token

    kp = _get_or_create_keypair(client_id, legacy_token, key_path)
    nonce = _get_nonce(client_id)
    device_jwt = _build_device_jwt(client_id, kp, nonce, scope)
    token = _exchange_for_plex_token(client_id, device_jwt).strip()

    # 7-day lifetime
    expires_at = int(time.time()) + 7 * 24 * 60 * 60
    _save_token(token_path, token, expires_at)

    return token

def plex_headers() -> dict:
    return {
        "X-Plex-Token": get_plex_token()
    }


if __name__ == "__main__":
    t = get_plex_token()
    print("Plex token (truncated):", t[:60], "...")