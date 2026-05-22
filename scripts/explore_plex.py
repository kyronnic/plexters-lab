from plexter.plex.client import PlexClient


def main() -> None:
    client = PlexClient()

    print("Libraries:")
    for library in client.get_libraries():
        print(f"- {library.get('title')} [{library.get('type')}] key={library.get('key')}")

    print("\nTV libraries:")
    for library in client.get_libraries_by_type("show"):
        print(f"- {library.get('title')} key={library.get('key')}")

    query = "Frieren"
    print(f"\nSearching shows for: {query}")

    shows = client.search_shows(query)

    for i, show in enumerate(shows, start=1):
        print(
            f"{i}. {show.get('title')} "
            f"library={show.get('_libraryTitle')} "
            f"ratingKey={show.get('ratingKey')}"
        )

    if shows:
        selected = shows[0]
        print(f"\nEpisodes for: {selected.get('title')}")

        episodes = client.get_show_episodes(selected["ratingKey"])

        for ep in episodes[:10]:
            print(
                f"S{ep.get('parentIndex', 0):02}E{ep.get('index', 0):02} "
                f"- {ep.get('title')} "
                f"ratingKey={ep.get('ratingKey')}"
            )

        print(f"\nTotal episodes found: {len(episodes)}")

    client.close()


if __name__ == "__main__":
    main()