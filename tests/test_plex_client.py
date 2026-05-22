import httpx
import pytest

from plexter.plex.client import PlexClient


def test_create_video_playlist_posts_plex_playlist_uri() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)

        if request.url.path == "/identity":
            return httpx.Response(
                200,
                json={"MediaContainer": {"machineIdentifier": "machine-123"}},
            )

        if request.url.path == "/playlists":
            return httpx.Response(200, json={"MediaContainer": {"size": 1}})

        return httpx.Response(404)

    client = PlexClient(base_url="http://plex.test", token="token")
    client.client = httpx.Client(
        base_url=client.base_url,
        transport=httpx.MockTransport(handler),
    )

    response = client.create_video_playlist(
        "Anime Round Robin",
        ["episode-a", "episode-b"],
    )

    assert response == {"MediaContainer": {"size": 1}}
    assert requests[1].method == "POST"
    assert requests[1].url.path == "/playlists"
    assert requests[1].url.params["type"] == "video"
    assert requests[1].url.params["title"] == "Anime Round Robin"
    assert requests[1].url.params["uri"] == (
        "server://machine-123/com.plexapp.plugins.library"
        "/library/metadata/episode-a,episode-b"
    )

    client.close()


def test_create_video_playlist_requires_title() -> None:
    client = PlexClient(base_url="http://plex.test", token="token")

    with pytest.raises(ValueError, match="title"):
        client.create_video_playlist("", ["episode-a"])

    client.close()


def test_create_video_playlist_requires_rating_keys() -> None:
    client = PlexClient(base_url="http://plex.test", token="token")

    with pytest.raises(ValueError, match="rating key"):
        client.create_video_playlist("Anime Round Robin", [])

    client.close()
