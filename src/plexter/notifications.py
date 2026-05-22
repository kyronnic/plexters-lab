from collections.abc import Mapping, Sequence
from typing import Any

from psycopg.types.json import Json

import httpx

from plexter.config import settings
from plexter.db import get_connection


DiscordEmbedField = Mapping[str, Any]


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
    *,
    title: str | None = None,
    description: str | None = None,
    color: int | None = None,
    fields: Sequence[DiscordEmbedField] | None = None,
) -> int:
    payload = build_discord_payload(
        message=message,
        title=title,
        description=description,
        color=color,
        fields=fields,
    )

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
        json=payload,
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


def notify_success(
    message: str,
    metadata: dict[str, Any] | None = None,
    *,
    title: str | None = None,
    description: str | None = None,
    color: int | None = None,
    fields: Sequence[DiscordEmbedField] | None = None,
) -> int:
    return send_discord_message(
        message=f"✅ {message}",
        event_type="success",
        metadata=metadata,
        title=title,
        description=description,
        color=color,
        fields=fields,
    )


def notify_failure(
    message: str,
    metadata: dict[str, Any] | None = None,
    *,
    title: str | None = None,
    description: str | None = None,
    color: int | None = None,
    fields: Sequence[DiscordEmbedField] | None = None,
) -> int:
    return send_discord_message(
        message=f"❌ {message}",
        event_type="failure",
        metadata=metadata,
        title=title,
        description=description,
        color=color,
        fields=fields,
    )


def notify_info(
    message: str,
    metadata: dict[str, Any] | None = None,
    *,
    title: str | None = None,
    description: str | None = None,
    color: int | None = None,
    fields: Sequence[DiscordEmbedField] | None = None,
) -> int:
    return send_discord_message(
        message=f"ℹ️ {message}",
        event_type="info",
        metadata=metadata,
        title=title,
        description=description,
        color=color,
        fields=fields,
    )


def build_discord_payload(
    message: str,
    *,
    title: str | None = None,
    description: str | None = None,
    color: int | None = None,
    fields: Sequence[DiscordEmbedField] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"content": message}

    if not any((title, description, color is not None, fields)):
        return payload

    embed: dict[str, Any] = {}
    if title:
        embed["title"] = title
    if description:
        embed["description"] = description
    if color is not None:
        embed["color"] = normalize_discord_color(color)
    if fields:
        embed["fields"] = [normalize_discord_field(field) for field in fields]

    payload["embeds"] = [embed]
    return payload


def normalize_discord_color(color: int) -> int:
    if not 0 <= color <= 0xFFFFFF:
        raise ValueError("Discord embed color must be between 0 and 0xFFFFFF.")

    return color


def normalize_discord_field(field: DiscordEmbedField) -> dict[str, Any]:
    if "name" not in field:
        raise ValueError("Discord embed field is missing name.")
    if "value" not in field:
        raise ValueError("Discord embed field is missing value.")

    return {
        "name": str(field["name"]),
        "value": str(field["value"]),
        "inline": bool(field.get("inline", False)),
    }
