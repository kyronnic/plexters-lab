# Plexter Playlists

Playlist features live under `plexter.playlists`. Each playlist type should own its domain logic, command-line entry points, compatibility wrappers, and feature-specific documentation in its own subpackage.

## Round Robin

Round Robin lives in:

```text
src/plexter/playlists/round_robin/
    __init__.py       # Public package exports
    round_robin.py    # Core round-robin domain logic
    cli.py            # `plexter-round-robin` command implementation
    preview.py        # Compatibility preview/create wrapper
```

### What It Does

Round Robin creates an episode order by alternating between selected shows.

Example:

```text
Frieren S01E01
The Apothecary Diaries S01E01
Frieren S01E02
The Apothecary Diaries S01E02
...
```

If one show runs out of episodes, it is skipped and the remaining shows continue.

### Main Entry Point

Use the package command from the repository root:

```bash
uv run plexter-round-robin
```

Subcommands:

- `preview`: show selected shows, ordered episodes, and rating keys.
- `keys`: print only the ordered episode rating keys.
- `create`: create a Plex video playlist.

### Preview

```bash
uv run plexter-round-robin preview \
  "Apothecary Diaries" \
  "Frieren"
```

### Print Rating Keys

```bash
uv run plexter-round-robin keys \
  "Apothecary Diaries" \
  "Frieren"
```

### Create a Plex Playlist

```bash
uv run plexter-round-robin create \
  "Apothecary Diaries" \
  "Frieren" \
  --title "Anime Round Robin"
```

### Useful Options

Limit total playlist length:

```bash
uv run plexter-round-robin preview \
  "Apothecary Diaries" \
  "Frieren" \
  --limit 20
```

Limit printed preview rows:

```bash
uv run plexter-round-robin preview \
  "Apothecary Diaries" \
  "Frieren" \
  --preview-count 10
```

Filter to a Plex TV library:

```bash
uv run plexter-round-robin preview \
  "Apothecary Diaries" \
  "Frieren" \
  --library "TV"
```

Create with a limit:

```bash
uv run plexter-round-robin create \
  "Apothecary Diaries" \
  "Frieren" \
  --limit 24 \
  --title "Anime Round Robin - 24 Episodes"
```

### Execution Logging

Every execution logs a row to `script_runs` through `plexter.db.log_script_run`.

- `preview` and `keys` log `dry_run=true`.
- `create` logs `dry_run=false`.
- Successful runs include playlist name, selected shows, episode count, and dry-run status.
- Failed runs include the error message, selected show queries, and playlist name when available.

### Missing Show Errors

If Plex cannot find a title, the command exits with a clean error:

```text
error: No show found for query: Some Show. Tried Plex search terms: Some Show, Some, Show.
```

When that happens:

- Confirm the show exists in a Plex TV library.
- Try the exact Plex title.
- Try a shorter search term.
- Use `--library` if the show is in a specific library.

### Compatibility Wrapper

The old preview script has moved into the round-robin package:

```bash
uv run python -m plexter.playlists.round_robin.preview \
  "Apothecary Diaries" \
  "Frieren"
```

New usage should prefer `uv run plexter-round-robin ...`.
