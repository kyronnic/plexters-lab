from dotenv import load_dotenv
load_dotenv()

import os
from plexapi.server import PlexServer

from plexlib.plex_jwt_auth import get_plex_token

BASE = os.environ["PLEX_SERVER_URL"].rstrip("/")
TOKEN = get_plex_token(force_refresh=True)

print("Token prefix:", TOKEN[:8], "dots:", TOKEN.count("."))

plex = PlexServer(BASE, TOKEN)

print("CONNECTED")
print("Server name:", plex.friendlyName)
print("Libraries:", [s.title for s in plex.library.sections()])
