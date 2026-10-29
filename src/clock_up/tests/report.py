import re

from testsweet import catch_exceptions, params, test

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
from clock_up._report import confirmation, error_message, status
from clock_up._timeline import Session, Timeline
from clock_up.tests._helpers import LOG, LONDON, assert_raised_like, utc


@test
def confirms_in_and_out():
    text_in = confirmation('in', utc(2026, 10, 1, 9), LONDON)
    text_out = confirmation('out', utc(2026, 10, 1, 17), LONDON)
    assert text_in == 'Clocked in on Thu 2026-10-01 at 09:00:00 BST'
    assert text_out == 'Clocked out on Thu 2026-10-01 at 17:00:00 BST'


@test
def status_never_clocked_in():
    text = status(Timeline(), utc(2026, 10, 1, 9), LONDON)
    assert text == 'Never clocked in'


@test
def status_clocked_in_matches_readme_shape():
    now = utc(2026, 10, 1, 10, 23, 45)
    timeline = Timeline(
        (
            Session(utc(2026, 9, 1, 9), utc(2026, 9, 6, 1)),  # 112h in Sep
            Session(utc(2026, 9, 28, 9), utc(2026, 9, 28, 17)),  # week + Sep
            Session(utc(2026, 10, 1, 9), None),
        )
    )
    text = status(timeline, now, LONDON)
    assert text == (
        'Clocked in for 01:23:45\n'
        'Clocked in since 09:00:00 BST today\n'
        '\n'
        ' 09:23:45 clocked this week\n'
        ' 01:23:45 clocked so far in Oct 2026\n'
        '120:00:00 clocked in Sep 2026'
    )


@test
def status_clocked_out():
    now = utc(2026, 10, 1, 19, 15)
    timeline = Timeline((Session(utc(2026, 10, 1, 9), utc(2026, 10, 1, 17)),))
    text = status(timeline, now, LONDON)
    assert text == (
        'Clocked out for 02:15:00\n'
        'Clocked out since 17:00:00 BST today\n'
        '\n'
        '08:00:00 clocked this week\n'
        '08:00:00 clocked so far in Oct 2026\n'
        '00:00:00 clocked in Sep 2026'
    )


@test
def status_since_yesterday():
    now = utc(2026, 10, 2, 8)
    timeline = Timeline((Session(utc(2026, 10, 1, 21), None),))
    text = status(timeline, now, LONDON)
    second_line = text.splitlines()[1]
    assert second_line == 'Clocked in since 21:00:00 BST yesterday'


@test
@params(
    [
        (
            AlreadyClockedIn(utc(2026, 10, 1, 9)),
            False,
            'Already clocked in since 09:00:00 BST today',
        ),
        (NotClockedIn(), False, 'Not clocked in'),
        (
            InFuture(utc(2026, 10, 2, 9)),
            True,
            '--since must be in the past',
        ),
        (
            NotAfterLast(utc(2026, 9, 30, 9)),
            True,
            '--since must be after the last event, 2026-09-30 09:00:00 BST',
        ),
        (
            NotAfterLast(utc(2026, 10, 1, 12)),
            False,
            'Last event 12:00:00 BST today is not before now',
        ),
        (BadSince('noon'), True, "Cannot parse --since: 'noon'"),
        (
            StartsWithOut(path=LOG, lineno=4, at=utc(2026, 10, 1, 9)),
            False,
            'clock.log:4: out at 2026-10-01 09:00:00 BST '
            'is the first event; expected in',
        ),
        (
            NotAlternating(
                path=LOG,
                lineno=7,
                kind='in',
                at=utc(2026, 10, 1, 9),
                previous_lineno=2,
            ),
            False,
            'clock.log:7: in at 2026-10-01 09:00:00 BST follows in at line 2',
        ),
        (
            SharedTimestamp(
                path=LOG,
                lineno=3,
                kind='out',
                at=utc(2026, 10, 1, 9),
                previous_kind='in',
                previous_lineno=5,
            ),
            False,
            'clock.log:3: out at 2026-10-01 09:00:00 BST '
            'has the same time as in at line 5',
        ),
        (
            BadLine(
                path=LOG,
                lineno=2,
                line='garbage',
                reason='expected "<kind> <timestamp>"',
            ),
            False,
            "clock.log:2: cannot parse 'garbage': "
            'expected "<kind> <timestamp>"',
        ),
        (
            IoFailure(path=LOG, reason='Is a directory'),
            False,
            'clock.log: Is a directory',
        ),
    ]
)
def phrases_errors(exc, since_given, expected):
    now = utc(2026, 10, 1, 12)
    text = error_message(exc, now, LONDON, since_given)
    assert text == expected


# One of every ClockUpError subclass, each carrying a datetime where
# the class has one.
EVERY_ERROR = [
    AlreadyClockedIn(utc(2026, 10, 1, 9)),
    NotClockedIn(),
    InFuture(utc(2026, 10, 2, 9)),
    NotAfterLast(utc(2026, 9, 30, 9)),
    BadSince('noon'),
    BadLine(path=LOG, lineno=1, line='xyz', reason='unknown kind'),
    StartsWithOut(path=LOG, lineno=4, at=utc(2026, 10, 1, 9)),
    NotAlternating(
        path=LOG,
        lineno=7,
        kind='in',
        at=utc(2026, 10, 1, 9),
        previous_lineno=2,
    ),
    SharedTimestamp(
        path=LOG,
        lineno=3,
        kind='out',
        at=utc(2026, 10, 1, 9),
        previous_kind='in',
        previous_lineno=5,
    ),
    IoFailure(path=LOG, reason='Is a directory'),
]


def _all_subclasses(cls):
    for sub in cls.__subclasses__():
        yield sub
        yield from _all_subclasses(sub)


@test
def every_error_subclass_is_listed():
    listed = {type(exc) for exc in EVERY_ERROR}
    defined = set(_all_subclasses(ClockUpError))
    assert listed == defined


@test
@params(
    [
        (exc, since_given)
        for exc in EVERY_ERROR
        for since_given in (False, True)
    ]
)
def every_error_is_phrased_in_local_time(exc, since_given):
    now = utc(2026, 10, 1, 12)
    text = error_message(exc, now, LONDON, since_given)
    iso_stamp = re.search(r'\d{2}T\d{2}', text)
    assert '+00:00' not in text
    assert iso_stamp is None


@test
def unphrased_error_is_a_bug():
    now = utc(2026, 10, 1, 12)
    with catch_exceptions() as excs:
        error_message(ClockUpError(), now, LONDON, False)
    assert_raised_like(excs, TypeError())
