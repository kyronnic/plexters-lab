import base64
import hashlib
import json
import os
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