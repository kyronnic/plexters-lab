from datetime import datetime, timezone

from plexter.services.activity import get_recent_activity, summarize_activity


class FakeCursor:
    def __init__(self) -> None:
        self.rows: list[tuple] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def execute(self, query: str, params: tuple[int]) -> None:
        limit = params[0]

        if "FROM script_runs" in query:
            self.rows = [
                (
                    datetime(2026, 5, 22, 12, 0, tzinfo=timezone.utc),
                    "round_robin",
                    "success",
                    "Created playlist",
                ),
                (
                    datetime(2026, 5, 22, 10, 0, tzinfo=timezone.utc),
                    "health_check",
                    "success",
                    "OK",
                ),
            ][:limit]
            return

        if "FROM notifications" in query:
            self.rows = [
                (
                    datetime(2026, 5, 22, 13, 0, tzinfo=timezone.utc),
                    "success",
                    "sent",
                    "Discord sent",
                    "discord",
                ),
            ][:limit]
            return

        self.rows = []

    def fetchall(self) -> list[tuple]:
        return self.rows


class FakeConnection:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def cursor(self) -> FakeCursor:
        return FakeCursor()


def test_get_recent_activity_combines_and_sorts_descending() -> None:
    activities = get_recent_activity(
        limit=3,
        connection_factory=FakeConnection,
    )

    assert [activity["source"] for activity in activities] == [
        "notifications",
        "script_runs",
        "script_runs",
    ]
    assert activities[0]["summary"] == "success - sent - Discord sent"
    assert activities[1]["summary"] == "round_robin - success - Created playlist"


def test_get_recent_activity_rejects_non_positive_limit() -> None:
    assert get_recent_activity(limit=0, connection_factory=FakeConnection) == []


def test_summarize_activity_handles_empty_values() -> None:
    assert summarize_activity(None, None, None) == "Activity recorded"
