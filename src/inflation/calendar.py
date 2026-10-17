"""Decide which releases are due: past their scheduled time, not yet published, still fresh.

This is what `inflation due` runs at the start of every release-watch job (SPEC §4.6),
so it must stay fast and must never touch the network.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta

from inflation.config import CalendarEntry

# After this long we stop polling and let a human look: a release that hasn't appeared
# 12 hours after its scheduled time usually means a postponement or a calendar error.
MAX_AGE = timedelta(hours=12)


def due_releases(
    entries: Iterable[CalendarEntry],
    published_ids: set[str],
    now_utc: datetime,
    max_age: timedelta = MAX_AGE,
) -> list[CalendarEntry]:
    due = [
        entry
        for entry in entries
        if entry.release_id not in published_ids
        and entry.scheduled_utc <= now_utc < entry.scheduled_utc + max_age
    ]
    return sorted(due, key=lambda entry: entry.scheduled_utc)
