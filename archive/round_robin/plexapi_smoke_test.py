from dotenv import load_dotenv
load_dotenv()

from plexlib.plex_client import get_plex

plex = get_plex()

print("Connected to:", plex.friendlyName)
print("Libraries:", [s.title for s in plex.library.sections()])
