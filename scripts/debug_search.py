from plexter.plex.client import PlexClient

client = PlexClient()

libraries = client.get_libraries()

for lib in libraries:
    print(
        lib.get("title"),
        lib.get("type"),
        lib.get("key"),
    )

client.close()