from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from plexter.db import get_connection
from plexter.plex.client import PlexClient


@dataclass(frozen=True)
class ServiceCheck:
    name: str
    connected: bool
    message: str | None = None


@dataclass(frozen=True)
class PlexHealth(ServiceCheck):
    library_count: int = 0


@dataclass(frozen=True)
class SystemStatus:
    atlas_online: bool
    plex: PlexHealth
    postgres: ServiceCheck

    @property
    def library_count(self) -> int:
        return self.plex.library_count


PlexClientFactory = Callable[[], PlexClient]
ConnectionFactory = Callable[[], Any]


def check_plex(
    client_factory: PlexClientFactory = PlexClient,
) -> PlexHealth:
    try:
        client = client_factory()
        try:
            libraries = client.get_libraries()
        finally:
            client.close()
    except Exception as exc:
        return PlexHealth(
            name="Plex",
            connected=False,
            message=str(exc),
            library_count=0,
        )

    return PlexHealth(
        name="Plex",
        connected=True,
        message="Connected",
        library_count=len(libraries),
    )


def check_postgres(
    connection_factory: ConnectionFactory = get_connection,
) -> ServiceCheck:
    try:
        with connection_factory() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                cur.fetchone()
    except Exception as exc:
        return ServiceCheck(
            name="Postgres",
            connected=False,
            message=str(exc),
        )

    return ServiceCheck(
        name="Postgres",
        connected=True,
        message="Connected",
    )


def get_system_status(
    plex_client_factory: PlexClientFactory = PlexClient,
    postgres_connection_factory: ConnectionFactory = get_connection,
) -> SystemStatus:
    return SystemStatus(
        atlas_online=True,
        plex=check_plex(client_factory=plex_client_factory),
        postgres=check_postgres(connection_factory=postgres_connection_factory),
    )
