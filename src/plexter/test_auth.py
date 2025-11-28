from plex_jwt_auth import get_plex_token, plex_headers
import httpx

def main():
    token = get_plex_token()
    print("Token (truncated):", token[:40], "...")

    resp = httpx.get(
        "https://clients.plex.tv/api/v2/user",
        headers=plex_headers()
    )
    print("Status:", resp.status_code)
    print(resp.text[:200])

if __name__ == "__main__":
    main()