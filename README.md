# Plexter

Plexter is a Python application and automation platform for managing a personal Plex ecosystem. The project is currently focused on Plex automation, round-robin playlist generation, notifications, service health checks, and a PostgreSQL-backed foundation for future metadata, recommendation, Discord, and AI-powered media services.

Infrastructure lives outside this repository in `~/plexstack`. This repository is application code only.

## Current Capabilities

- Load configuration from `.env` through `plexter.config`.
- Connect to PostgreSQL through `plexter.db`.
- Log notification events through `plexter.notifications`.
- Connect to Plex with classic `X-Plex-Token` authentication.
- Enumerate Plex libraries and TV shows.
- Search Plex globally and fetch show episodes.
- Build round-robin episode orders across multiple shows.
- Preview round-robin playlist contents from the command line.
- Create Plex video playlists from round-robin episode order.

## Repository Layout

```text
src/
    plexter/
        config.py              # .env-backed application settings
        db.py                  # PostgreSQL connection and script run logging
        notifications.py       # Notification logging and Discord webhook entry point
        discord_bot/           # Discord slash-command bot skeleton
        plex/
            client.py          # Plex API client
        playlists/
            README.md          # Playlist feature documentation
            round_robin/       # Round-robin playlist package
        services/
            health.py          # Service health support

scripts/
    explore_plex.py            # Inspect Plex libraries and episode lookup
    debug_search.py            # Simple Plex library search helper
    test_db_log.py             # Manual DB logging smoke script
    test_notifications.py      # Manual notification smoke script
    test_plex_client.py        # Manual Plex client smoke script

tests/
    test_discord_bot.py        # Unit tests for bot setup
    test_discord_bot_commands.py # Unit tests for bot command formatting
    test_round_robin.py        # Unit tests for round-robin logic
    test_round_robin_cli.py    # Unit tests for round-robin CLI flow
    test_plex_client.py        # Mocked tests for Plex playlist creation

docs/
    project_state.md           # Development state and notes
    services.md                # Long-running application service notes
```

## Requirements

- Python matching the project setting in `pyproject.toml`.
- `uv` for dependency and virtual environment management.
- Plex server reachable from this machine.
- PostgreSQL for persistent application state.
- A `.env` file with the required settings.

The project was initialized with `uv`. Run commands through `uv run ...` from the repository root.

## Configuration

Configuration is loaded from `.env` by `plexter.config`.

Required for Plex features:

```env
PLEX_BASE_URL=http://your-plex-host:32400
PLEX_TOKEN=your-classic-plex-token
```

Required for database-backed features:

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=plexter
POSTGRES_USER=plexter
POSTGRES_PASSWORD=your-password
```

Optional for Discord notifications:

```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

Required for the Discord slash-command bot:

```env
DISCORD_BOT_TOKEN=your_bot_token
DISCORD_GUILD_ID=your_server_id
```

Do not hardcode secrets in source files. Classic Plex token authentication is the current working default; do not replace it with JWT authentication.

## Plex Client

Plex API access belongs in `plexter.plex.client.PlexClient`.

Current useful methods include:

- `get_server_identity()`
- `get_machine_identifier()`
- `get_libraries()`
- `get_libraries_by_type()`
- `get_library_items()`
- `get_shows()`
- `search()`
- `search_shows()`
- `get_metadata()`
- `get_show_seasons()`
- `get_season_episodes()`
- `get_show_episodes()`
- `create_video_playlist()`

Known Plex server note: `/library/sections/{id}/search` has returned HTTP 400 on this server, so round-robin show lookup uses global `/search` first, then falls back to scanning TV library titles.

## Playlists

Playlist features live under `src/plexter/playlists/`. Round Robin is currently the first concrete playlist feature and has its own package, CLI, compatibility wrapper, and documentation.

See [src/plexter/playlists/README.md](src/plexter/playlists/README.md) for Round Robin usage and implementation details.

## Discord Bot

The Discord bot skeleton lives under `src/plexter/discord_bot/` and uses `discord.py` slash commands with guild-scoped registration for fast testing. It does not enable the message content intent.

Run it from the repository root:

```bash
uv run python -m plexter.discord_bot
```

Current commands:

- `/ping`
- `/libraries`
- `/search query:<str>`

Service/runtime notes for Atlas Bot live in [docs/services.md](docs/services.md).

## Development

Run the focused tests:

```bash
uv run pytest tests/test_round_robin.py tests/test_round_robin_cli.py tests/test_plex_client.py
```

Run lint checks:

```bash
uv run ruff check src scripts tests
```

If the environment cannot write to the default `uv` cache, point it at `/tmp`:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_round_robin.py tests/test_round_robin_cli.py tests/test_plex_client.py
UV_CACHE_DIR=/tmp/uv-cache uv run ruff check src scripts tests
```

## Persistence and Notifications

PostgreSQL is the source of truth for persistent application state. Do not add local JSON files for durable state.

Current database-backed areas:

- `script_runs`
- `service_health`
- `notifications`

Notifications should flow through `plexter.notifications`. Avoid direct Discord webhook calls elsewhere in the codebase.

## Roadmap

Immediate and short-term priorities:

- Round-robin playlist hardening.
- Plex playlist management.
- Discord webhook support.
- Bitwarden secret integration.
- Metadata synchronization.
- Service health monitoring.

Longer-term direction:

- User watch history.
- Recommendation engine.
- AI enrichment pipeline.
- Discord bot.
- AI-generated playlists.
- User preference tracking.
