# qBittorrent Integration

## Overview

The `plexter.qbittorrent` module provides a client for interacting with qBittorrent's Web API, enabling automated discovery and management of torrents.

## Modules

### `client.py`

The main qBittorrent client implementation.

**Classes:**

- `Torrent`: Dataclass representing a single torrent with properties for state detection
  - Properties: `is_stalled`, `is_inactive()`, `time_since_activity`
  
- `QBittorrentClient`: Main API client
  - `authenticate()`: Authenticate with qBittorrent
  - `get_torrents(filter_)`: Get torrents with optional filtering
  - `get_stalled_torrents()`: Get only stalled torrents
  - `get_inactive_torrents(hours)`: Get torrents inactive for N hours

**Example Usage:**

```python
from plexter.qbittorrent.client import QBittorrentClient

client = QBittorrentClient(
    base_url="http://localhost:8080",
    username="admin",
    password="adminpass"
)

if client.authenticate():
    stalled = client.get_stalled_torrents()
    for torrent in stalled:
        print(f"{torrent.name}: {torrent.state}")
    client.close()
```

## Configuration

Set environment variables (or store in Bitwarden):

```bash
QBITTORRENT_BASE_URL=http://localhost:8080
QBITTORRENT_USERNAME=admin
QBITTORRENT_PASSWORD=your_password
```

## Torrent States

qBittorrent torrent states include:

- `allocating`: Allocating disk space
- `downloading`: Actively downloading
- `forcedDL`: Forced download
- `metaDL`: Downloading metadata
- `missingFiles`: Files are missing
- `paused`: Paused
- `queuedForChecking`: Queued for checking
- `seeding`: Actively seeding
- `stalledDL`: Stalled downloading (no peers)
- `stalledUP`: Stalled uploading (no seeds)
- `forcedUP`: Forced upload
- `checkingResumeData`: Checking resume data
- `error`: Error state

## Discord Integration

The `/stalled` Discord bot command uses this module to report stalled torrents:

```
/stalled hours:48
```

This returns all stalled and inactive (for >48 hours) torrents from qBittorrent.

## Limitations

- Only qBittorrent is currently supported (Overseerr/Arrs integration pending)
- Requires qBittorrent API v2 (standard in modern qBittorrent)
- VPN/network access to qBittorrent required from the Plexter host
