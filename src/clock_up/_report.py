from datetime import datetime, tzinfo

from clock_up._errors import (
    AlreadyClockedIn,
    BadLine,
    BadSince,
    ClockUpError,
    InFuture,
    IoFailure,
    NotAfterLast,
    NotAlternating,
    NotClockedIn,
    SharedTimestamp,
    StartsWithOut,
)
from clock_up._events import Kind
from clock_up._format import (
    DATE_FORMAT,
    TIME_FORMAT,
    format_duration,
    format_stamp,
    time_phrase,
)
from clock_up._timeline import Timeline, totals


def confirmation(kind: Kind, at: datetime, tz: tzinfo) -> str:
    local = at.astimezone(tz)
    date, clock = local.strftime(DATE_FORMAT), local.strftime(TIME_FORMAT)
    return f'Clocked {kind} on {date} at {clock}'


def status(timeline: Timeline, now: datetime, tz: tzinfo) -> str:
    last_event_at = timeline.last_at
    if last_event_at is None:
        return 'Never clocked in'
    state = 'in' if timeline.clocked_in else 'out'
    elapsed = now - last_event_at
    summary = totals(timeline, now, tz)
    rows = [
        (summary.week_total, 'clocked this week'),
        (
            summary.month_total,
            f'clocked so far in {summary.month_start:%b %Y}',
        ),
        (
            summary.prev_month_total,
            f'clocked in {summary.prev_month_start:%b %Y}',
        ),
    ]
    texts = [format_duration(duration) for duration, _ in rows]
    width = max(map(len, texts))
    return '\n'.join(
        [
            f'Clocked {state} for {format_duration(elapsed)}',
            f'Clocked {state} since {time_phrase(last_event_at, now, tz)}',
            '',
            *(
                f'{text:>{width}} {label}'
                for text, (_, label) in zip(texts, rows, strict=True)
            ),
        ]
    )


def _where(
    exc: BadLine | StartsWithOut | NotAlternating | SharedTimestamp,
) -> str:
    """The ``path:lineno`` of the log line an error is about."""
    return f'{exc.path}:{exc.lineno}'


def error_message(
    exc: ClockUpError, now: datetime, tz: tzinfo, since_given: bool
) -> str:
    """Phrase ``exc`` for the user, in ``tz``.

    ``since_given`` says whether the event time came from ``--since``,
    so that messages only mention the option when it was used.
    """
    match exc:
        case AlreadyClockedIn():
            return (
                f'Already clocked in since {time_phrase(exc.since, now, tz)}'
            )
        case NotClockedIn():
            return 'Not clocked in'
        case InFuture():
            if since_given:
                return '--since must be in the past'
            return f'{format_stamp(exc.at, tz)} is in the future'
        case NotAfterLast():
            if since_given:
                return (
                    '--since must be after the last event, '
                    f'{format_stamp(exc.last, tz)}'
                )
            return (
                f'Last event {time_phrase(exc.last, now, tz)} '
                'is not before now'
            )
        case BadSince():
            return f'Cannot parse --since: {exc.text!r}'
        case BadLine():
            return f'{_where(exc)}: cannot parse {exc.line!r}: {exc.reason}'
        case StartsWithOut():
            return (
                f'{_where(exc)}: out at {format_stamp(exc.at, tz)} '
                'is the first event; expected in'
            )
        case NotAlternating():
            return (
                f'{_where(exc)}: {exc.kind} at '
                f'{format_stamp(exc.at, tz)} follows {exc.kind} '
                f'at line {exc.previous_lineno}'
            )
        case SharedTimestamp():
            return (
                f'{_where(exc)}: {exc.kind} at '
                f'{format_stamp(exc.at, tz)} has the same time as '
                f'{exc.previous_kind} at line {exc.previous_lineno}'
            )
        case IoFailure():
            return f'{exc.path}: {exc.reason}'
        case _:
            raise TypeError(f'No message for {exc!r}')
