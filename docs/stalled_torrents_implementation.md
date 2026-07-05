# Stalled Torrents Implementation Summary

## Overview

Complete implementation for discovering stalled/inactive torrents in qBittorrent and manually searching for replacement torrents using qBittorrent search plugins.

## Changes Made

### 1. qBittorrent Client Module (`plexter.qbittorrent`)

**Files Created:**
- [src/plexter/qbittorrent/__init__.py](src/plexter/qbittorrent/__init__.py)
- [src/plexter/qbittorrent/client.py](src/plexter/qbittorrent/client.py)

**Features:**
- `Torrent` dataclass with state detection (`is_stalled`, `is_inactive()`)
- `QBittorrentClient` with methods:
  - `authenticate()`: Connect to qBittorrent Web API
  - `get_torrents(filter_)`: Get filtered torrent list
  - `get_stalled_torrents()`: Get only stalled torrents
  - `get_inactive_torrents(hours)`: Get torrents with no activity for N hours

**Implementation Uses:**
- `httpx` for HTTP requests (already in dependencies)
- Supports qBittorrent Web API v2
- Type hints and dataclasses for clean design

### 2. Stalled Torrents Discovery Service

**Files Created:**
- [src/plexter/services/torrents.py](src/plexter/services/torrents.py)

**Features:**
- `get_stalled_torrents()`: Discover stalled/inactive torrents from qBittorrent
- `format_stalled_torrents_message()`: Format results for Discord display
- `StalledTorrentInfo` dataclass: Clean torrent data representation
- Filters by state and inactivity threshold (default 48 hours)
- Calculates time inactive in human-readable format

### 3. Discord Bot Command

**Files Modified:**
- [src/plexter/discord_bot/commands.py](src/plexter/discord_bot/commands.py)

**New Command:** `/stalled [hours]`
- Returns all stalled and inactive torrents from qBittorrent
- Optional `hours` parameter for inactivity threshold (default: 48)
- Displays up to 20 torrents with detailed information:
  - Name, state, progress, ratio
  - Time inactive, size, ratio
  - Source (qBittorrent)

**Example Usage:**
```
/stalled              # Show all stalled/inactive torrents (>48h)
/stalled hours:72     # Show torrents inactive for >72 hours
```

### 4. Configuration Updates

**Files Modified:**
- [src/plexter/config.py](src/plexter/config.py)

**New Settings:**
```python
QBITTORRENT_BASE_URL     # Base URL of qBittorrent (e.g., http://localhost:8080)
QBITTORRENT_USERNAME     # qBittorrent username
QBITTORRENT_PASSWORD     # qBittorrent password
```

Store these in `.env` or Bitwarden Secrets Manager as usual.

### 5. Test Coverage

**Files Created:**
- [tests/test_qbittorrent_client.py](tests/test_qbittorrent_client.py)

**Tests Include:**
- Torrent dataclass state detection
- Client authentication (success/failure)
- Torrent retrieval
- Stalled torrent filtering
- Session management

## Setup Instructions

### 1. Configure qBittorrent Access

Add to `.env` or Bitwarden:
```bash
QBITTORRENT_BASE_URL=http://localhost:8080
QBITTORRENT_USERNAME=admin
QBITTORRENT_PASSWORD=your_qbittorrent_password
```

**Note:** qBittorrent runs via Gluetun VPN in your setup. The base URL depends on your network configuration:
- If Plexter runs on the host: `http://gluetun:8080` or through Nginx proxy
- If Plexter runs in a container on the same network: `http://qbittorrent:8080`

### 2. Update Plexter Environment

Reload Plexter to pick up new configuration:
```bash
cd /home/ktcarter96/plexters-lab
uv sync  # Ensure dependencies are current

# Run with Bitwarden secrets (if using BWS)
/home/ktcarter96/plexstack/scripts/bws-run.sh uv run python -m plexter.discord_bot

# OR run locally with .env (development only)
python -m plexter.discord_bot
```

**Important:** When running in production with Bitwarden Secrets Manager, always use the `bws-run.sh` wrapper. This injects secrets from `/etc/plexter/bws.env` into the environment before Plexter starts.

### 3. Add qBittorrent Search Plugins

See [Services/qBittorrent-Search-Plugins.md](/Services/qBittorrent-Search-Plugins.md) for detailed instructions.

**Quick Start:**
```bash
mkdir -p ./appdata/qbittorrent/qBittorrent/searchPlugins

# Download popular plugins
cd ./appdata/qbittorrent/qBittorrent/searchPlugins/
curl -o 1337x.py https://raw.githubusercontent.com/qbittorrent/search-plugins/master/nova3/engines/1337x.py
curl -o torrentz2.py https://raw.githubusercontent.com/qbittorrent/search-plugins/master/nova3/engines/torrentz2.py

# Restart qBittorrent
docker restart qbittorrent
```

## Workflow

### Finding and Replacing Stalled Torrents

1. **Identify Stalled Torrents:**
   ```
   /stalled hours:48
   ```
   This returns all torrents that have been stalled or inactive for >48 hours

2. **Access qBittorrent Search:**
   - Open qBittorrent Web UI
   - Navigate to the "Search" tab
   - Select search plugins to use (check the boxes)

3. **Manual Search:**
   - Search for the specific stalled torrent name
   - Review results from multiple plugins
   - Download a replacement torrent

4. **Replace or Remove:**
   - Option A: Remove old torrent, add new one
   - Option B: Manually search in qBittorrent for specific episodes

## Architecture Decisions

### Why qBittorrent First?

Currently only qBittorrent is supported because:
- Direct Web API v2 access is straightforward
- Arrs (Sonarr/Radarr) don't expose torrent-level data the same way
- Overseerr is request-focused, not torrent-focused

**Future Enhancement:** Can be extended to query:
- Sonarr/Radarr for completed items with missing seeds
- Overseerr for stuck requests

### httpx vs requests

Using `httpx` because:
- Already in Plexter dependencies
- Modern async-ready library
- Better for future async integration

### Discord Message Formatting

Limited to 20 torrents per message due to Discord embed limits. Long lists are truncated with "...and N more" indicator.

## Troubleshooting

### Command Not Showing

1. Verify config loaded:
   ```bash
   cd /home/ktcarter96/plexters-lab
   /home/ktcarter96/plexstack/scripts/bws-run.sh uv run python -c "from plexter.config import settings; print(settings.qbit_base_url)"
   ```

2. Ensure `QBIT_BASE_URL`, `QBIT_USER`, `QBIT_PASSWORD` secrets are in Bitwarden

3. Restart Discord bot with `bws-run.sh`:
   ```bash
   pkill -f "python -m plexter.discord_bot" || true
   /home/ktcarter96/plexstack/scripts/bws-run.sh uv run python -m plexter.discord_bot
   ```

### Connection Failed

1. Check qBittorrent is running:
   ```bash
   docker logs qbittorrent
   ```

2. Verify network access (if containers on different networks):
   ```bash
   docker exec -it gluetun curl http://localhost:8080/api/v2/app/webapiVersion
   ```

3. Verify credentials are correct in qBittorrent web UI

4. Check firewall/network policies

### No Stalled Torrents Found

This is expected if:
- All torrents are healthy
- The threshold is too high (try lower hours value)
- No torrents match the inactive criteria

## Future Enhancements

1. **Overseerr Integration:**
   - Query requests stuck in "pending" or "failed" states
   - Link back to Overseerr for request management

2. **Sonarr/Radarr Integration:**
   - Query for missing episodes/movies
   - Show which media still needs to be downloaded

3. **Automated Retry:**
   - Automatically re-search for stalled torrents at intervals
   - Remove stalled torrents if replacement found

4. **Statistics Tracking:**
   - Store historical data in PostgreSQL
   - Track how often torrents stall
   - Identify problematic indexers

5. **Smart Plugin Selection:**
   - Auto-select plugins based on region
   - Rotate plugins to avoid rate limiting

## Related Documentation

- [docs/qbittorrent_integration.md](/home/ktcarter96/plexters-lab/docs/qbittorrent_integration.md)
- [Services/qBittorrent-Search-Plugins.md](/home/ktcarter96/plex-codex/Services/qBittorrent-Search-Plugins.md)
- [Services/qBittorrent.md](/home/ktcarter96/plex-codex/Services/qBittorrent.md)
