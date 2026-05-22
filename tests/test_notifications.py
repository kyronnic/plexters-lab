import pytest

from plexter.notifications import (
    build_discord_payload,
    normalize_discord_color,
    normalize_discord_field,
    notify_success,
)


def test_build_discord_payload_without_embed_keeps_plain_message_shape() -> None:
    payload = build_discord_payload("Hello")

    assert payload == {"content": "Hello"}


def test_build_discord_payload_with_embed_fields() -> None:
    payload = build_discord_payload(
        "Round robin complete",
        title="Playlist Created",
        description="Anime Round Robin",
        color=0x2ECC71,
        fields=[
            {"name": "Episodes", "value": 24, "inline": True},
            {"name": "Dry Run", "value": False},
        ],
    )

    assert payload == {
        "content": "Round robin complete",
        "embeds": [
            {
                "title": "Playlist Created",
                "description": "Anime Round Robin",
                "color": 0x2ECC71,
                "fields": [
                    {"name": "Episodes", "value": "24", "inline": True},
                    {"name": "Dry Run", "value": "False", "inline": False},
                ],
            }
        ],
    }


def test_normalize_discord_color_rejects_out_of_range_color() -> None:
    with pytest.raises(ValueError, match="color"):
        normalize_discord_color(0x1000000)


def test_normalize_discord_field_requires_name_and_value() -> None:
    with pytest.raises(ValueError, match="name"):
        normalize_discord_field({"value": "missing name"})

    with pytest.raises(ValueError, match="value"):
        normalize_discord_field({"name": "missing value"})


def test_notify_success_keeps_existing_message_and_metadata_api(monkeypatch) -> None:
    calls: list[dict] = []

    def fake_send_discord_message(**kwargs):
        calls.append(kwargs)
        return 123

    monkeypatch.setattr(
        "plexter.notifications.send_discord_message",
        fake_send_discord_message,
    )

    result = notify_success("Done", {"job": "round_robin"})

    assert result == 123
    assert calls == [
        {
            "message": "✅ Done",
            "event_type": "success",
            "metadata": {"job": "round_robin"},
            "title": None,
            "description": None,
            "color": None,
            "fields": None,
        }
    ]


def test_notify_success_accepts_embed_kwargs(monkeypatch) -> None:
    calls: list[dict] = []

    def fake_send_discord_message(**kwargs):
        calls.append(kwargs)
        return 123

    monkeypatch.setattr(
        "plexter.notifications.send_discord_message",
        fake_send_discord_message,
    )

    result = notify_success(
        "Done",
        title="Playlist Created",
        description="Anime Round Robin",
        color=0x2ECC71,
        fields=[{"name": "Episodes", "value": 24}],
    )

    assert result == 123
    assert calls[0]["message"] == "✅ Done"
    assert calls[0]["title"] == "Playlist Created"
    assert calls[0]["description"] == "Anime Round Robin"
    assert calls[0]["color"] == 0x2ECC71
    assert calls[0]["fields"] == [{"name": "Episodes", "value": 24}]
