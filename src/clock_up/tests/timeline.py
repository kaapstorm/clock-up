from testsweet import catch_exceptions, params, test

from clock_up._errors import (
    AlreadyClockedIn,
    InFuture,
    NotAfterLast,
    NotAlternating,
    NotClockedIn,
    SharedTimestamp,
    StartsWithOut,
)
from clock_up._events import Event
from clock_up._timeline import Session, Timeline, check_append, validate
from clock_up.tests._helpers import LOG, assert_raised_like, utc


def _events(*pairs):
    return [
        Event(at, kind, lineno)
        for lineno, (at, kind) in enumerate(pairs, start=1)
    ]


def _timeline(*pairs):
    return validate(_events(*pairs), LOG)


@test
@params(
    [
        ([], ()),
        (
            [(utc(2026, 10, 1, 9), 'in')],
            (Session(utc(2026, 10, 1, 9), None),),
        ),
        (
            [(utc(2026, 10, 1, 9), 'in'), (utc(2026, 10, 1, 17), 'out')],
            (Session(utc(2026, 10, 1, 9), utc(2026, 10, 1, 17)),),
        ),
        (
            [
                (utc(2026, 10, 1, 9), 'in'),
                (utc(2026, 10, 1, 17), 'out'),
                (utc(2026, 10, 2, 9), 'in'),
            ],
            (
                Session(utc(2026, 10, 1, 9), utc(2026, 10, 1, 17)),
                Session(utc(2026, 10, 2, 9), None),
            ),
        ),
    ]
)
def validate_folds_alternating_events_into_sessions(pairs, expected):
    timeline = _timeline(*pairs)
    assert timeline == Timeline(expected)


@test
@params(
    [
        (
            [(utc(2026, 10, 1, 9), 'out')],
            StartsWithOut(path=LOG, lineno=1, at=utc(2026, 10, 1, 9)),
        ),
        (
            [(utc(2026, 10, 1, 9), 'in'), (utc(2026, 10, 1, 10), 'in')],
            NotAlternating(
                path=LOG,
                lineno=2,
                kind='in',
                at=utc(2026, 10, 1, 10),
                previous_lineno=1,
            ),
        ),
        (
            [
                (utc(2026, 10, 1, 9), 'in'),
                (utc(2026, 10, 1, 17), 'out'),
                (utc(2026, 10, 1, 18), 'out'),
            ],
            NotAlternating(
                path=LOG,
                lineno=3,
                kind='out',
                at=utc(2026, 10, 1, 18),
                previous_lineno=2,
            ),
        ),
        (
            [(utc(2026, 10, 1, 9), 'in'), (utc(2026, 10, 1, 9), 'out')],
            SharedTimestamp(
                path=LOG,
                lineno=2,
                kind='out',
                at=utc(2026, 10, 1, 9),
                previous_kind='in',
                previous_lineno=1,
            ),
        ),
    ]
)
def rejects_non_alternating(pairs, expected):
    with catch_exceptions() as excs:
        validate(_events(*pairs), LOG)
    assert_raised_like(excs, expected)


@test
@params(
    [
        (Timeline(), False, None),
        (
            Timeline((Session(utc(2026, 10, 1, 9), None),)),
            True,
            utc(2026, 10, 1, 9),
        ),
        (
            Timeline(
                (
                    Session(utc(2026, 9, 30, 9), utc(2026, 9, 30, 17)),
                    Session(utc(2026, 10, 1, 9), utc(2026, 10, 1, 17)),
                )
            ),
            False,
            utc(2026, 10, 1, 17),
        ),
    ]
)
def timeline_knows_current_state(timeline, clocked_in, last_at):
    actual_clocked_in = timeline.clocked_in
    actual_last_at = timeline.last_at
    assert actual_clocked_in is clocked_in
    assert actual_last_at == last_at


@test
def check_append_allows_valid_sequence():
    now = utc(2026, 10, 1, 9)
    check_append(Timeline(), 'in', now, now)
    timeline = _timeline((utc(2026, 9, 30, 9), 'in'))
    check_append(timeline, 'out', utc(2026, 9, 30, 18), now)


@test
@params(
    [
        (
            [],
            'in',
            utc(2026, 10, 1, 9, 0, 1),
            InFuture(utc(2026, 10, 1, 9, 0, 1)),
        ),
        ([], 'out', utc(2026, 10, 1, 8), NotClockedIn()),
        (
            [(utc(2026, 9, 30, 9), 'in'), (utc(2026, 9, 30, 17), 'out')],
            'out',
            utc(2026, 10, 1, 8),
            NotClockedIn(),
        ),
        (
            [(utc(2026, 10, 1, 8), 'in')],
            'in',
            utc(2026, 10, 1, 9),
            AlreadyClockedIn(utc(2026, 10, 1, 8)),
        ),
        (
            [(utc(2026, 9, 30, 9), 'in')],
            'out',
            utc(2026, 9, 30, 8),
            NotAfterLast(utc(2026, 9, 30, 9)),
        ),
        (
            [(utc(2026, 10, 1, 9), 'in')],
            'out',
            utc(2026, 10, 1, 9),  # same second as the last event
            NotAfterLast(utc(2026, 10, 1, 9)),
        ),
        (
            [(utc(2026, 10, 1, 9), 'in')],
            'in',
            utc(2026, 10, 1, 8, 30),  # before the last event, wrong kind
            AlreadyClockedIn(utc(2026, 10, 1, 9)),
        ),
        (
            [(utc(2026, 10, 1, 9), 'in')],
            'in',
            utc(2026, 10, 1, 9),  # same second, wrong kind
            AlreadyClockedIn(utc(2026, 10, 1, 9)),
        ),
        (
            [(utc(2026, 10, 1, 8), 'in')],
            'in',
            utc(2026, 10, 1, 9, 0, 1),  # in the future, wrong kind
            AlreadyClockedIn(utc(2026, 10, 1, 8)),
        ),
    ]
)
def check_append_refuses(pairs, kind, at, expected):
    now = utc(2026, 10, 1, 9)
    with catch_exceptions() as excs:
        check_append(_timeline(*pairs), kind, at, now)
    assert_raised_like(excs, expected)
