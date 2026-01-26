from plexter.legacy_auth import create_pin, build_auth_url, poll_pin
from plexlib.plex_jwt_auth import PLEX_CLIENT_ID

def main():
    pin_id, pin_code = create_pin()
    url = build_auth_url(PLEX_CLIENT_ID, pin_code, "https://localhost/plexter-success")
    print("1) Visit this URL in the browser and log into Plex:")
    print(url)
    print()
    print(f"2) Then come back here. PIN id = {pin_id}")

    token = poll_pin(pin_id)
    print("Got user access token")
    print(token)

if __name__ == "__main__":
    main()