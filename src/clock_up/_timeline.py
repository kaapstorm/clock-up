from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta, tzinfo
from pathlib import Path

from clock_up._errors import (
    AlreadyClockedIn,
    InFuture,
    NotAfterLast,
    NotAlternating,
    NotClockedIn,
    SharedTimestamp,
    StartsWithOut,
)
from clock_up._events import Event, Kind


@dataclass(frozen=True)
class Session:
    start: datetime
    end: datetime | None


@dataclass(frozen=True)
class Timeline:
    """Checked sessions in time order; only the last may be open."""

    sessions: tuple[Session, ...] = ()

    @property
    def clocked_in(self) -> bool:
        return bool(self.sessions) and self.sessions[-1].end is None

    @property
    def last_at(self) -> datetime | None:
        """The instant of the last event, or None if there are none."""
        if not self.sessions:
            return None
        last = self.sessions[-1]
        return last.start if last.end is None else last.end


def validate(events: list[Event], path: Path) -> Timeline:
    """Check the events and fold them into a Timeline.

    ``events`` must already be in time order, as ``load`` returns them.
    Raise ClockUpError unless they start with in and alternate, with no
    two at the same time. ``path`` is the log the events were read
    from, for the message.

    This is the only function that turns events into sessions, so
    nothing can work from a list that has not been checked.
    """
    sessions = []
    previous: Event | None = None
    for event in events:
        if previous is None:
            if event.kind != 'in':
                raise StartsWithOut(
                    path=path, lineno=event.lineno, at=event.at
                )
        elif event.at == previous.at:
            raise SharedTimestamp(
                path=path,
                lineno=event.lineno,
                kind=event.kind,
                at=event.at,
                previous_kind=previous.kind,
                previous_lineno=previous.lineno,
            )
        elif event.kind == previous.kind:
            raise NotAlternating(
                path=path,
                lineno=event.lineno,
                kind=event.kind,
                at=event.at,
                previous_lineno=previous.lineno,
            )
        elif event.kind == 'out':  # so previous is the matching in
            sessions.append(Session(previous.at, event.at))
        previous = event
    if previous is not None and previous.kind == 'in':
        sessions.append(Session(previous.at, None))
    return Timeline(tuple(sessions))


def check_append(
    timeline: Timeline,
    kind: Kind,
    at: datetime,
    now: datetime,
) -> None:
    """Raise ClockUpError unless ``kind`` at ``at`` can be appended."""
    # Kind first: no choice of ``at`` can fix a kind conflict.
    if kind == 'in' and timeline.clocked_in:
        raise AlreadyClockedIn(timeline.sessions[-1].start)
    if kind == 'out' and not timeline.clocked_in:
        raise NotClockedIn()
    if at > now:
        raise InFuture(at)
    last_at = timeline.last_at
    if last_at is not None and at <= last_at:
        raise NotAfterLast(last_at)


@dataclass(frozen=True)
class Totals:
    """Time clocked in each period, with the period starts used."""

    month_start: datetime
    prev_month_start: datetime
    week_total: timedelta
    month_total: timedelta
    prev_month_total: timedelta


def week_start(now: datetime, tz: tzinfo) -> datetime:
    """The start of the week containing ``now``: Sunday 00:00 in ``tz``."""
    local = now.astimezone(tz)
    days_since_sunday = local.isoweekday() % 7  # Sunday is 7
    day = local.date() - timedelta(days=days_since_sunday)
    return datetime.combine(day, time()).replace(tzinfo=tz)


def month_start(now: datetime, tz: tzinfo) -> datetime:
    local = now.astimezone(tz)
    return datetime(local.year, local.month, 1).replace(tzinfo=tz)


def prev_month_start(now: datetime, tz: tzinfo) -> datetime:
    return month_start(month_start(now, tz) - timedelta(days=1), tz)


def time_in_window(
    sessions: Sequence[Session],
    start: datetime,
    end: datetime,
    now: datetime,
) -> timedelta:
    """Time clocked from ``start`` to ``end``; an open session runs to now."""
    # Session instants are UTC, but the window ends may be period
    # starts built in tz. Two datetimes with the same ZoneInfo subtract
    # by wall clock, which is wrong across a DST change, so bring the
    # window into UTC before comparing and subtracting.
    window_start, window_end = start.astimezone(UTC), end.astimezone(UTC)
    total = timedelta()
    for session in sessions:
        overlap_start = max(session.start, window_start)
        overlap_end = min(session.end or now, window_end)
        if overlap_end > overlap_start:
            total += overlap_end - overlap_start
    return total


def totals(timeline: Timeline, now: datetime, tz: tzinfo) -> Totals:
    week_begins = week_start(now, tz)
    month_begins = month_start(now, tz)
    prev_month_begins = prev_month_start(now, tz)
    sessions = timeline.sessions
    return Totals(
        month_start=month_begins,
        prev_month_start=prev_month_begins,
        week_total=time_in_window(
            sessions, start=week_begins, end=now, now=now
        ),
        month_total=time_in_window(
            sessions, start=month_begins, end=now, now=now
        ),
        prev_month_total=time_in_window(
            sessions, start=prev_month_begins, end=month_begins, now=now
        ),
    )
