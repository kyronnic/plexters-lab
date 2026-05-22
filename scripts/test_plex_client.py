from plexter.plex.client import PlexClient

client = PlexClient()

identity = client.get_server_identity()
print("Server:", identity.get("MediaContainer", {}).get("machineIdentifier"))

libraries = client.get_libraries()
print("Libraries:")

for lib in libraries:
    print(f"- {lib.get('title')} [{lib.get('type')}] key={lib.get('key')}")

client.close()