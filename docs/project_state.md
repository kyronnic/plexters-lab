# Plexter Project State

Last Updated: May 2026

---

# Infrastructure Status

Infrastructure is hosted on a Beelink server running Ubuntu Linux.

Primary infrastructure repository:

~/plexstack

Major services:

- Plex
- Sonarr
- Radarr
- Prowlarr
- Overseerr
- Bazarr
- qBittorrent
- Gluetun
- PostgreSQL

PostgreSQL data is persisted under:

~/plexstack/appdata/postgres

---

# Plexters-Lab Status

Repository initialized using UV.

Current package structure:

src/
    plexter/
        plex/
        playlists/
        services/

scripts/
tests/
docs/

---

# Completed Work

## Configuration

Implemented:

plexter.config

BWS-backed settings with `.env` fallback loaded successfully from:

plexter.config

---

## Database

Implemented:

plexter.db

Verified:

- PostgreSQL connectivity
- Insert operations
- Query operations

Tables currently created:

- script_runs
- service_health
- notifications

---

## Notifications

Implemented:

plexter.notifications

Verified:

- Notification logging
- PostgreSQL integration

Discord webhook integration not yet configured.

---

## Plex Client

Implemented:

plexter.plex.client

Verified:

- Plex authentication via X-Plex-Token
- Server identity lookup
- Library enumeration
- Global search
- Episode enumeration

Working methods:

- get_server_identity()
- get_libraries()
- get_libraries_by_type()
- search()
- search_shows()
- get_show_episodes()

Known issue:

/library/sections/{id}/search

returns HTTP 400 on this server.

Global:

/search

works correctly.

---

# Verified Example

Search:

Frieren

Successfully returns:

Frieren: Beyond Journey's End

Episodes correctly enumerate:

S01E01
S01E02
S01E03
...

34 episodes detected.

---

# Next Development Tasks

## Immediate

- Implement round_robin.py
- Create round robin playlist builder
- Create Plex playlist creation helper

## Short-Term

- Discord webhook support
- Bitwarden integration
- Metadata sync services

## Medium-Term

- User watch history
- Recommendation engine
- AI enrichment pipeline

## Long-Term

- Discord bot
- Plexter assistant
- AI-generated playlists
- User preference tracking

---

# Important Notes

Authentication uses:

PLEX_TOKEN

stored in:

.env

Do not use JWT authentication.

Classic Plex token authentication is working and should remain the default implementation.

PostgreSQL should be used as the persistence layer for all future application features.
