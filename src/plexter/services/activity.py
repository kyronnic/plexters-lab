from __future__ import annotations

from collections.abc import Callable
from typing import Any

from plexter.db import get_connection


ConnectionFactory = Callable[[], Any]


def get_recent_activity(
    limit: int = 5,
    connection_factory: ConnectionFactory = get_connection,
) -> list[dict[str, Any]]:
    if limit < 1:
        return []

    activities = [
        *get_recent_script_runs(limit, connection_factory),
        *get_recent_notifications(limit, connection_factory),
    ]

    return sorted(
        activities,
        key=lambda activity: activity["timestamp"],
        reverse=True,
    )[:limit]


def get_recent_script_runs(
    limit: int,
    connection_factory: ConnectionFactory,
) -> list[dict[str, Any]]:
    with connection_factory() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    COALESCE(ended_at, started_at) AS activity_timestamp,
                    script_name,
                    status,
                    message
                FROM script_runs
                ORDER BY COALESCE(ended_at, started_at) DESC
                LIMIT %s;
                """,
                (limit,),
            )
            rows = cur.fetchall()

    return [
        {
            "source": "script_runs",
            "timestamp": row[0],
            "name": row[1],
            "status": row[2],
            "message": row[3],
            "summary": summarize_activity(row[1], row[2], row[3]),
        }
        for row in rows
    ]


def get_recent_notifications(
    limit: int,
    connection_factory: ConnectionFactory,
) -> list[dict[str, Any]]:
    with connection_factory() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    sent_at AS activity_timestamp,
                    event_type,
                    status,
                    message,
                    channel
                FROM notifications
                ORDER BY sent_at DESC
                LIMIT %s;
                """,
                (limit,),
            )
            rows = cur.fetchall()

    return [
        {
            "source": "notifications",
            "timestamp": row[0],
            "name": row[1],
            "status": row[2],
            "message": row[3],
            "channel": row[4],
            "summary": summarize_activity(row[1], row[2], row[3]),
        }
        for row in rows
    ]


def summarize_activity(
    name: str | None,
    status: str | None,
    message: str | None,
) -> str:
    parts = [part for part in (name, status, message) if part]
    return " - ".join(parts) if parts else "Activity recorded"
