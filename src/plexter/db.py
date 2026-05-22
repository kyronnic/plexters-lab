from datetime import datetime, timezone
from typing import Any

import psycopg
from psycopg.types.json import Json

from plexter.config import settings


def get_connection():
    return psycopg.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        dbname=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password,
    )


def log_script_run(
    script_name: str,
    status: str,
    message: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> int:
    now = datetime.now(timezone.utc)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO script_runs
                    (script_name, status, started_at, ended_at, duration_seconds, message, metadata)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
                """,
                (
                    script_name,
                    status,
                    now,
                    now,
                    0,
                    message,
                    Json(metadata or {}),
                ),
            )
            row = cur.fetchone()
            if row is None:
                raise RuntimeError("Failed to insert script run.")
            return row[0]