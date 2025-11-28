import base64
import hashlib
import json
import os
import platform
import time
from dataclasses import dataclass
from pathlib import Path

import httpx
import jwt
from dotenv import load_dotenv
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

# Assign project directory
THIS_FILE = Path(__file__).resolve()
PROJECT_ROOT = THIS_FILE.parents[2]

# Load environment variables
load_dotenv(PROJECT_ROOT / ".env")

PLEX_CLIENT_ID = os.getenv("PLEX_CLIENT_ID")
PLEX_LEGACY_TOKEN = os.getenv("PLEX_LEGACY_TOKEN")

if not PLEX_CLIENT_ID:
    raise RuntimeError("PLEX_CLIENT_ID not set in .env")

# Project config directory
CONFIG_DIR = PROJECT_ROOT / "config"
CONFIG_DIR.mkdir(exist_ok=True)
KEY_PATH = CONFIG_DIR / "device_ed25519.key"
TOKEN_PATH = CONFIG_DIR / "plex_jwt_token.json"

PLEX_BASE = "https://clients.plex.tv/api/v2/auth"

def _b64url(data: bytes) -> str:
    """Base64 URL encode without '=' padding"""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

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

# Keypair storage
def _save_keypair(kp: Keypair) -> None:
    KEY_PATH.write_text(
        json.dumps(
            {
                "private": _b64url(kp.private_bytes),
                "public": _b64url(kp.public_bytes)
            },
            indent=2
        )
    )
    os.chmod(KEY_PATH, 0o600)

def _load_keypair() -> Keypair | None:
    if not KEY_PATH.exists():
        return None

    try:
        raw = KEY_PATH.read_text().strip()
        if not raw:
            return None

        data = json.loads(KEY_PATH.read_text())
        private_bytes = base64.urlsafe_b64decode(data["private"] + "===")
        public_bytes = base64.urlsafe_b64decode(data["public"] + "===")
        return Keypair(private_bytes=private_bytes, public_bytes=public_bytes)
    except Exception:
        return None

def _generate_keypair() -> Keypair:
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
    _save_keypair(kp)
    return kp

def _get_or_create_keypair() -> Keypair:
    kp = _load_keypair()
    if kp is not None:
        return kp

    if not PLEX_LEGACY_TOKEN:
        raise RuntimeError(
            "No device key found and PLEX_TOKEN is not set in .env. "
            "You need a legacy Plex token once to register the device JWK"
        )

    kp = _generate_keypair()
    _register_device_jwk(kp)
    return kp

# HTTP helpers
def _base_headers() -> dict:
    return {
        "X-Plex-Client-Identifier": PLEX_CLIENT_ID,
        "X-Plex-Product": "Plexter",
        "X-Plex-Version": "0.1.0",
        "X-Plex-Device": "Plexter Dev Client",
        "X-Plex-Platform": "macOS",
        "X-Plex-Platform-Version": platform.mac_ver()[0] or "0.0"
    }

# JWK registration
def _register_device_jwk(kp: Keypair) -> None:
    """
    Register this device's public JWK with Plex using the legacy token.
    This only needs to happen once per client_id
    :param kp:
    :return:
    """
    if not PLEX_LEGACY_TOKEN:
        raise RuntimeError("PLEX_TOKEN is required in .env to register JWK")

    headers = _base_headers()
    headers["X-Plex-Token"] = PLEX_LEGACY_TOKEN

    body = {"jwk": kp.public_jwk}

    resp = httpx.post(f"{PLEX_BASE}/jwk", headers=headers, json=body, timeout=10)
    resp.raise_for_status()

# Token cache
def _load_cached_token():
    if not TOKEN_PATH.exists():
        return None
    try:
        data = json.loads(TOKEN_PATH.read_text())
        return data["token"], int(data["expires_at"])
    except Exception:
        return None

def _save_token(token: str, expires_at: int) -> None:
    TOKEN_PATH.write_text(
        json.dumps({"token": token, "expires_at": int(expires_at)}, indent=2)
    )

# JWT flow: nonce -> device JWT -> Plex token
def _get_nonce() -> str:
    resp = httpx.get(f"{PLEX_BASE}/nonce", headers=_base_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()["nonce"]

def _build_device_jwt(kp: Keypair, nonce: str, scope: str) -> str:
    now = int(time.time())
    payload = {
        "nonce": nonce,
        "scope": scope,
        "aud": "plex.tv",
        "iss": PLEX_CLIENT_ID,
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

def _exchange_for_plex_token(device_jwt: str) -> str:
    body = {"jwt": device_jwt}
    resp = httpx.post(
        f"{PLEX_BASE}/token", headers=_base_headers(), json=body, timeout=10
    )

    resp.raise_for_status()
    data = resp.json()
    return data["auth_token"]

# Public API
def get_plex_token(
        scope: str = "username,email,friendly_name",
        force_refresh: bool = False
) -> str:
    """
    Return a valid Plex JWT auth token.
    - Uses cached token if still valid
    - Otherwis goes through nonce -> device JWT -> Plex JWT flow
    :param scope:
    :param force_refresh:
    :return:
    """
    if not force_refresh:
        cached = _load_cached_token()
        if cached:
            token, exp = cached
            if exp > time.time() + 60:
                return token

    kp = _get_or_create_keypair()
    nonce = _get_nonce()
    device_jwt = _build_device_jwt(kp, nonce, scope)
    token = _exchange_for_plex_token(device_jwt)

    # 7-day lifetime
    expires_at = int(time.time()) + 7 * 24 * 60 * 60
    _save_token(token, expires_at)

    return token

def plex_headers() -> dict:
    return {
        "X-Plex-Token": get_plex_token()
    }

def _test_legacy_token():
    print("PLEX_CLIENT_ID:", repr(PLEX_CLIENT_ID))
    print("PLEX_LEGACY_TOKEN (first 10 chars):", repr((PLEX_LEGACY_TOKEN or "")[:10]))

    if not PLEX_LEGACY_TOKEN:
        print("No PLEX_TOKEN set in .env")
        return

    headers = {
        "X-Plex-Client-Identifier": PLEX_CLIENT_ID,
        "X-Plex-Token": PLEX_LEGACY_TOKEN,
    }

    resp = httpx.get(
        "https://plex.tv/api/v2/user",
        headers=headers,
        timeout=10,
    )
    print("Legacy token test status:", resp.status_code)
    print("Body snippet:", resp.text[:200])


if __name__ == "__main__":
    t = get_plex_token()
    print("Plex token (truncated):", t[:60], "...")