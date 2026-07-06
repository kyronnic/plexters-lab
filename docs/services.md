# Plexter Services

This document tracks long-running Plexter application services. Infrastructure services such as Plex, PostgreSQL, Sonarr, Radarr, and related containers are managed separately in `~/plexstack`.

## Atlas Bot

Atlas Bot is the Plexter Discord slash-command bot. It runs from this application repository and is managed by `systemd` so it remains running after shell sessions end.

### Purpose

Atlas Bot provides Discord slash commands for Plexter.

Current commands:

- `/ping`: confirms the bot is online.
- `/status`: shows Atlas, Plex, Postgres, and Plex library status.
- `/recent`: shows the latest Plexter script and notification activity.
- `/libraries`: lists Plex libraries.
- `/search query:<str>`: searches Plex shows and returns the top results.
- `/youtube-download url:<str>`: downloads a YouTube video or playlist into the YouTube Plex libraries.

### Runtime Entry Point

The bot starts through the package entry point:

```bash
uv run python -m plexter.discord_bot
```

The bot does not use the Discord message content intent. Commands are registered as guild-scoped slash commands for fast testing.

### Required Environment

The service expects Plexter configuration through `plexter.config`. Bitwarden Secrets Manager is read first when `BWS_ACCESS_TOKEN` and `PLEXTER_BWS_ORGANIZATION_ID` are available, then `.env` is used as a fallback.

For systemd, load the server-local BWS bootstrap file before starting the app:

```env
EnvironmentFile=/etc/plexter/bws.env
```

Required bot settings:

```env
DISCORD_BOT_TOKEN=your_bot_token
DISCORD_GUILD_ID=your_server_id
```

The `/libraries` and `/search` commands also require:

```env
PLEX_BASE_URL=http://your-plex-host:32400
PLEX_TOKEN=your-classic-plex-token
```

YouTube downloads use `yt-dlp` and default to this library root:

```env
YOUTUBE_LIBRARY_ROOT=/mnt/media/Library/YouTube
```

The command infers the destination from the URL. Single videos go to
`$YOUTUBE_LIBRARY_ROOT/Movies`; playlist URLs go to
`$YOUTUBE_LIBRARY_ROOT/TV/<Series>/Season NN`. Create the Plex libraries
manually:

- `YouTube Movies` pointed at `/media/Library/YouTube/Movies`
- `YouTube TV` pointed at `/media/Library/YouTube/TV`

Run production bot commands through the `plexstack/scripts/bws-run.sh` wrapper so
BWS-backed settings are available to the process.

### Systemd Operations

Check service status:

```bash
systemctl status atlas.service
```

Follow logs:

```bash
journalctl -u atlas.service -f
```

Restart the bot:

```bash
sudo systemctl restart atlas.service
```

Stop the bot:

```bash
sudo systemctl stop atlas.service
```

Start the bot:

```bash
sudo systemctl start atlas.service
```

### Notes

- The service should be restarted after changes to bot code, BWS bootstrap config, or `.env` fallback values.
- Guild-scoped slash command sync happens during bot startup.
- The bot code lives in `src/plexter/discord_bot/`.
- The app entry point lives in `src/plexter/discord_bot/__main__.py`.
