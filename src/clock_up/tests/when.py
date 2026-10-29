import os
import tempfile
from datetime import UTC, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from testsweet import catch_exceptions, params, tag, test

from clock_up._errors import BadSince
from clock_up._when import local_zone, parse_since
from clock_up.tests._helpers import LONDON, assert_raised_like, dt

NOW = dt(2026, 10, 1, 9)  # Thursday 09:00 BST


@test
@params(
    [
        ('21:00', dt(2026, 9, 30, 21)),  # README example: yesterday
        ('08:59', dt(2026, 10, 1, 8, 59)),  # earlier today
        ('09:00', dt(2026, 9, 30, 9)),  # equal to now -> yesterday
        ('08:30:15', dt(2026, 10, 1, 8, 30, 15)),
        ('2026-09-30 18:00', dt(2026, 9, 30, 18)),
        ('2026-09-30T18:00', dt(2026, 9, 30, 18)),
        ('2026-09-30 18:00:30', dt(2026, 9, 30, 18, 0, 30)),
        ('2026-09-30T18:00:30', dt(2026, 9, 30, 18, 0, 30)),
    ]
)
def parses_since(text, expected):
    result = parse_since(text, NOW, LONDON)
    zone = result.tzinfo
    assert result == expected
    assert zone is UTC


@test
def since_in_other_dst_period_gets_that_offset():
    now = dt(2026, 10, 29, 9)  # GMT
    result = parse_since('2026-10-20 09:00', now, LONDON)
    assert result == datetime(2026, 10, 20, 8, tzinfo=UTC)  # 09:00 BST


@test
@params(
    [
        # Just after the October change: yesterday 21:00 was BST.
        (dt(2026, 10, 25, 9), '21:00', datetime(2026, 10, 24, 20, tzinfo=UTC)),
        # Just after the March change: yesterday 21:00 was GMT.
        (dt(2026, 3, 29, 9), '21:00', datetime(2026, 3, 28, 21, tzinfo=UTC)),
    ]
)
def bare_time_yesterday_across_dst_keeps_wall_clock(now, text, expected):
    result = parse_since(text, now, LONDON)
    assert result == expected


@test
def since_in_missing_dst_hour_is_read_as_gmt():
    # 01:30 does not exist on 29 March; ZoneInfo reads it with the GMT
    # offset that applied just before, which is 02:30 BST.
    now = dt(2026, 3, 30, 9)
    result = parse_since('2026-03-29 01:30', now, LONDON)
    assert result == datetime(2026, 3, 29, 1, 30, tzinfo=UTC)


@test
@params(
    [
        ('',),
        ('noon',),
        ('25:00',),
        ('2026-13-01 09:00',),
        ('2026-09-30',),
        ('9pm',),
    ]
)
def rejects_bad_since(text):
    with catch_exceptions() as excs:
        parse_since(text, NOW, LONDON)
    assert_raised_like(excs, BadSince(text))


@test
def rejects_since_out_of_range():
    tokyo = ZoneInfo('Asia/Tokyo')
    with catch_exceptions() as excs:
        parse_since('0001-01-01 00:00', NOW, tokyo)
    assert_raised_like(excs, BadSince('0001-01-01 00:00'))


@test
@tag('posix')
def zone_from_tz_env():
    zone = local_zone({'TZ': 'Europe/Paris'})
    assert zone == ZoneInfo('Europe/Paris')


@test
@tag('posix')
def zone_from_posix_style_tz_env():
    zone = local_zone({'TZ': ':Europe/Paris'})
    assert zone == ZoneInfo('Europe/Paris')


@test
@tag('posix')
def zone_from_localtime_symlink():
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / 'usr' / 'share' / 'zoneinfo' / 'Europe' / 'Paris'
        target.parent.mkdir(parents=True)
        target.touch()
        link = Path(tmp) / 'localtime'
        os.symlink(target, link)
        zone = local_zone({}, localtime=link)
    assert zone == ZoneInfo('Europe/Paris')


@test
@tag('posix')
def zone_falls_back_to_fixed_offset():
    with tempfile.TemporaryDirectory() as tmp:
        zone = local_zone({'TZ': 'Not/AZone'}, localtime=Path(tmp) / 'absent')
    is_fixed = isinstance(zone, timezone)
    assert is_fixed


@test
@tag('posix')
@params([('dangling',), ('loop',)])
def zone_falls_back_when_localtime_link_is_broken(case):
    with tempfile.TemporaryDirectory() as tmp:
        link = Path(tmp) / 'localtime'
        if case == 'dangling':
            os.symlink(Path(tmp) / 'zoneinfo' / 'Not' / 'AZone', link)
        else:
            os.symlink(link, link)
        zone = local_zone({}, localtime=link)
    is_fixed = isinstance(zone, timezone)
    assert is_fixed
