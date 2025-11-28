import time
import httpx
from urllib.parse import urlencode
import xml.etree.ElementTree as ET

from plexter.plex_jwt_auth import _base_headers


def create_pin():
    headers = _base_headers().copy()
    headers["Accept"] = "application/json"

    resp = httpx.post(
        "https://plex.tv/api/v2/pins?strong=true",
        headers=_base_headers(),
        timeout=10,
        follow_redirects=True
    )

    print("PIN create status", resp.status_code)
    print("PIN create body snippet:", resp.text[:300])

    resp.raise_for_status()

    ctype = resp.headers.get("content-type", "")
    if "application/json" in ctype:
        data = resp.json()
        return data["id"], data["code"]

    root = ET.fromstring(resp.text)
    pin_id = int(root.attrib["id"])
    code = root.attrib["code"]
    return pin_id, code

def build_auth_url(client_id: str, pin_code: str, forward_url: str) -> str:
    params = {
        "clientID": client_id,
        "code": pin_code,
        "context[device][product]": "Plexter",
        "forwardUrl": forward_url
    }
    return "https://app.plex.tv/auth#?" + urlencode(params)

def poll_pin(pin_id: int, interval: float = 2.0, timeout: float = 300.0):
    start = time.time()
    while time.time() - start < timeout:
        resp = httpx.get(
            f"https://plex.tv/api/v2/pins/{pin_id}",
            headers=_base_headers(),
            timeout=10
        )
        resp.raise_for_status()
        ctype = resp.headers.get("content-type", "")
        if "application/json" in ctype:
            data = resp.json()
            return data["authToken"]

        root = ET.fromstring(resp.text)
        auth_token = root.attrib["authToken"]
        if auth_token:
            return auth_token
        time.sleep(interval)
    raise TimeoutError("PIN was never claimed")