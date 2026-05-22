from typing import Any
from psycopg.types.json import Json

import httpx

from plexter.config import settings
from plexter.db import get_connection


def log_notification(
    channel: str,
    event_type: str,
    status: str,
    message: str,
    metadata: dict[str, Any] | None = None,
) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO notifications
                    (channel, event_type, status, message, metadata)
                VALUES
                    (%s, %s, %s, %s, %s)
                RETURNING id;
                """,
                (
                    channel,
                    event_type,
                    status,
                    message,
                    Json(metadata or {}),
                ),
            )
            row = cur.fetchone()
            if row is None:
                raise RuntimeError("Failed to log notification.")
            return row[0]


def send_discord_message(
    message: str,
    event_type: str = "general",
    metadata: dict[str, Any] | None = None,
) -> int:
    if not settings.discord_webhook_url:
        print(f"[discord disabled] {message}")
        return log_notification(
            channel="discord",
            event_type=event_type,
            status="skipped",
            message=message,
            metadata=metadata,
        )

    response = httpx.post(
        settings.discord_webhook_url,
        json={"content": message},
        timeout=10,
    )

    response.raise_for_status()

    return log_notification(
        channel="discord",
        event_type=event_type,
        status="sent",
        message=message,
        metadata=metadata,
    )


def notify_success(message: str, metadata: dict[str, Any] | None = None) -> int:
    return send_discord_message(
        message=f"✅ {message}",
        event_type="success",
        metadata=metadata,
    )


def notify_failure(message: str, metadata: dict[str, Any] | None = None) -> int:
    return send_discord_message(
        message=f"❌ {message}",
        event_type="failure",
        metadata=metadata,
    )


def notify_info(message: str, metadata: dict[str, Any] | None = None) -> int:
    return send_discord_message(
        message=f"ℹ️ {message}",
        event_type="info",
        metadata=metadata,
    )