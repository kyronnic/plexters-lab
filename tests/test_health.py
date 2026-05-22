from plexter.services.health import (
    check_plex,
    check_postgres,
    get_system_status,
)


class FakePlexClient:
    def __init__(self, libraries: list[dict] | None = None) -> None:
        self.libraries = libraries or [{"title": "TV"}, {"title": "Movies"}]
        self.closed = False

    def get_libraries(self) -> list[dict]:
        return self.libraries

    def close(self) -> None:
        self.closed = True


class FakeCursor:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def execute(self, query: str) -> None:
        self.query = query

    def fetchone(self) -> tuple[int]:
        return (1,)


class FakeConnection:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def cursor(self) -> FakeCursor:
        return FakeCursor()


def test_check_plex_returns_connected_and_library_count() -> None:
    health = check_plex(client_factory=FakePlexClient)

    assert health.connected is True
    assert health.library_count == 2
    assert health.message == "Connected"


def test_check_plex_returns_failure() -> None:
    def client_factory() -> FakePlexClient:
        raise RuntimeError("plex unavailable")

    health = check_plex(client_factory=client_factory)

    assert health.connected is False
    assert health.library_count == 0
    assert health.message == "plex unavailable"


def test_check_postgres_runs_lightweight_query() -> None:
    health = check_postgres(connection_factory=FakeConnection)

    assert health.connected is True
    assert health.message == "Connected"


def test_check_postgres_returns_failure() -> None:
    def connection_factory() -> FakeConnection:
        raise RuntimeError("postgres unavailable")

    health = check_postgres(connection_factory=connection_factory)

    assert health.connected is False
    assert health.message == "postgres unavailable"


def test_get_system_status_combines_checks() -> None:
    status = get_system_status(
        plex_client_factory=FakePlexClient,
        postgres_connection_factory=FakeConnection,
    )

    assert status.atlas_online is True
    assert status.plex.connected is True
    assert status.postgres.connected is True
    assert status.library_count == 2
