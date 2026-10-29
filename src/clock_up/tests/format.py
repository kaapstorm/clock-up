from datetime import timedelta

from testsweet import params, test

from clock_up._format import format_duration, format_stamp, time_phrase
from clock_up.tests._helpers import LONDON, dt


@test
@params(
    [
        (timedelta(0), '00:00:00'),
        (timedelta(hours=1, minutes=23, seconds=45), '01:23:45'),
        (timedelta(hours=24), '24:00:00'),
        (timedelta(hours=120), '120:00:00'),
        (timedelta(hours=1, seconds=0.9), '01:00:00'),
    ]
)
def formats_duration(td, expected):
    text = format_duration(td)
    assert text == expected


@test
@params(
    [
        (
            dt(2026, 10, 1, 9),
            dt(2026, 10, 1, 10, 23, 45),
            '09:00:00 BST today',
        ),
        (dt(2026, 9, 30, 21), dt(2026, 10, 1, 9), '21:00:00 BST yesterday'),
        (
            dt(2026, 9, 29, 9),
            dt(2026, 10, 1, 9),
            '09:00:00 BST on Tue 2026-09-29',
        ),
        (
            dt(2026, 10, 24, 9),
            dt(2026, 10, 26, 9),
            '09:00:00 BST on Sat 2026-10-24',
        ),
        (dt(2026, 10, 26, 9), dt(2026, 10, 26, 10), '09:00:00 GMT today'),
    ]
)
def phrases_time(at, now, expected):
    text = time_phrase(at, now, LONDON)
    assert text == expected


@test
def stamps_in_zone():
    text = format_stamp(dt(2026, 9, 30, 9), LONDON)
    assert text == '2026-09-30 09:00:00 BST'
