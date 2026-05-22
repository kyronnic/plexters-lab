# Plexter

Plexter is a Python application and automation platform for managing, enhancing, and extending a personal Plex ecosystem.

## Purpose

Plexter provides:

- Plex automation
- Playlist generation
- Metadata enrichment
- User activity tracking
- Recommendation systems
- Discord integrations
- Future AI-powered media services

The project is intended to evolve into a modular service platform built around a central PostgreSQL database.

---

# Architecture

## Infrastructure Repository

Infrastructure is managed separately in:

~/plexstack

Infrastructure includes:

- Plex
- Sonarr
- Radarr
- Prowlarr
- Overseerr
- Bazarr
- qBittorrent
- Gluetun
- PostgreSQL
- Future monitoring stack

Infrastructure concerns should remain outside this repository.

---

## Application Repository

This repository contains application code only.

Current structure:

src/
    plexter/
        plex/
        playlists/
        services/

scripts/
tests/
docs/

---

# Technical Standards

## Python

- Python 3.12+
- Use type hints
- Prefer dataclasses for domain models
- Avoid global state
- Keep functions focused

## Database

PostgreSQL is the source of truth.

All persistent state should be stored in PostgreSQL.

Do not use local JSON files for persistent application data.

## Configuration

Configuration is loaded from:

.env

through:

plexter.config

Secrets should never be hardcoded.

Future secret management will use Bitwarden CLI.

## Notifications

All notifications should flow through:

plexter.notifications

Avoid direct Discord calls elsewhere in the codebase.

## Plex API

All Plex API interactions belong in:

plexter.plex.client

Avoid making raw HTTP requests outside the Plex client.

---

# Current Development Priorities

1. Round Robin playlist creation
2. Plex playlist management
3. Discord webhook integration
4. Bitwarden secret integration
5. Metadata synchronization
6. Service health monitoring
7. AI-powered recommendation systems

---

# Long-Term Vision

Plexter should become a platform capable of:

- Creating custom playlists
- Tracking user watch activity
- Recommending media
- Managing requests
- Interacting through Discord
- Integrating with AI services
- Serving as a control layer for the Plex ecosystem