from datetime import UTC, datetime, timedelta

from inflation.calendar import due_releases
from inflation.config import CalendarEntry


def _entry(release_id: str, day: int) -> CalendarEntry:
    # Synthetic schedule: releases at 12:00 UTC on the given day of January 2026.
    return CalendarEntry.model_validate(
        {
            "release_id": release_id,
            "indicator": "TEST",
            "reference_period": "2025-12",
            "release_date": f"2026-01-{day:02d}",
            "release_time_local": "12:00",
            "timezone": "UTC",
            "source_url": "https://example.org",
        }
    )


ENTRIES = [_entry("a", 10), _entry("b", 11), _entry("c", 12)]
NOON_11 = datetime(2026, 1, 11, 12, 0, tzinfo=UTC)


def test_due_at_scheduled_minute() -> None:
    assert [e.release_id for e in due_releases(ENTRIES, set(), NOON_11)] == ["b"]


def test_not_due_before_scheduled_time() -> None:
    assert due_releases(ENTRIES, set(), NOON_11 - timedelta(minutes=1)) == []


def test_published_releases_are_skipped() -> None:
    assert due_releases(ENTRIES, {"b"}, NOON_11 + timedelta(hours=1)) == []


def test_stale_releases_are_dropped_after_max_age() -> None:
    late = NOON_11 + timedelta(hours=12)
    assert due_releases(ENTRIES, set(), late) == []


def test_results_sorted_by_schedule() -> None:
    later = NOON_11 + timedelta(days=1, hours=1)
    entries = list(reversed(ENTRIES))
    result = due_releases(entries, set(), later, max_age=timedelta(days=3))
    assert [e.release_id for e in result] == ["a", "b", "c"]
