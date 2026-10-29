from datetime import timedelta

from testsweet import params, test

from clock_up._timeline import (
    Session,
    Timeline,
    month_start,
    prev_month_start,
    time_in_window,
    totals,
    week_start,
)
from clock_up.tests._helpers import LONDON, utc


@test
@params(
    [
        # Thursday -> previous Sunday
        (utc(2026, 10, 1, 9), utc(2026, 9, 27, 0)),
        # Sunday is its own week start
        (utc(2026, 9, 27, 9), utc(2026, 9, 27, 0)),
        # Saturday
        (utc(2026, 10, 3, 23), utc(2026, 9, 27, 0)),
        # week containing the DST change
        (utc(2026, 10, 29, 9), utc(2026, 10, 25, 0)),
        # week starts at 00:00 GMT, before the 01:00 change to BST
        (utc(2026, 4, 1, 9), utc(2026, 3, 29, 0)),
    ]
)
def finds_week_start(now, expected):
    start = week_start(now, LONDON)
    assert start == expected


@test
def finds_month_starts_across_dst():
    now = utc(2026, 10, 29, 9)  # GMT day
    this_month = month_start(now, LONDON)
    prev_month = prev_month_start(now, LONDON)
    this_offset = this_month.utcoffset()
    prev_offset = prev_month.utcoffset()
    assert this_month == utc(2026, 10, 1, 0)
    assert this_offset == timedelta(hours=1)  # 1 Oct is BST
    assert prev_month == utc(2026, 9, 1, 0)
    assert prev_offset == timedelta(hours=1)


@test
def finds_period_starts_after_dst_start():
    now = utc(2026, 4, 6, 9)  # Monday, BST
    week = week_start(now, LONDON)
    month = month_start(now, LONDON)
    prev_month = prev_month_start(now, LONDON)
    week_offset = week.utcoffset()
    month_offset = month.utcoffset()
    prev_offset = prev_month.utcoffset()
    assert week == utc(2026, 4, 5, 0)
    assert week_offset == timedelta(hours=1)
    assert month == utc(2026, 4, 1, 0)
    assert month_offset == timedelta(hours=1)
    assert prev_month == utc(2026, 3, 1, 0)
    assert prev_offset == timedelta(0)  # 1 Mar is GMT


@test
@params(
    [
        # wraps the year
        (utc(2026, 1, 15, 9), utc(2025, 12, 1, 0)),
        # first instant
        (utc(2026, 1, 1, 0), utc(2025, 12, 1, 0)),
        # long to short
        (utc(2026, 3, 31, 23, 59), utc(2026, 2, 1, 0)),
    ]
)
def finds_prev_month_start(now, expected):
    start = prev_month_start(now, LONDON)
    assert start == expected


@test
def time_in_window_sums_overlaps_and_open_session():
    now = utc(2026, 10, 1, 10, 23, 45)
    sessions = [
        # crosses Sunday 00:00
        Session(utc(2026, 9, 26, 22), utc(2026, 9, 27, 2)),
        # crosses month end
        Session(utc(2026, 9, 30, 20), utc(2026, 10, 1, 1)),
        # open
        Session(utc(2026, 10, 1, 9), None),
    ]
    week = time_in_window(
        sessions, start=utc(2026, 9, 27, 0), end=now, now=now
    )
    assert week == timedelta(hours=2 + 5) + timedelta(
        hours=1, minutes=23, seconds=45
    )


@test
def session_across_month_end_splits_between_months():
    now = utc(2026, 10, 1, 10)
    sessions = [Session(utc(2026, 9, 30, 20), utc(2026, 10, 1, 1))]
    this_month = month_start(now, LONDON)
    september = time_in_window(
        sessions,
        start=prev_month_start(now, LONDON),
        end=this_month,
        now=now,
    )
    october = time_in_window(sessions, start=this_month, end=now, now=now)
    assert september == timedelta(hours=4)
    assert october == timedelta(hours=1)


@test
def open_session_before_week_start_counts_from_sunday():
    now = utc(2026, 9, 27, 3)
    sessions = [Session(utc(2026, 9, 26, 22), None)]
    week = time_in_window(
        sessions, start=utc(2026, 9, 27, 0), end=now, now=now
    )
    assert week == timedelta(hours=3)


@test
def session_across_dst_end_is_true_elapsed():
    sessions = [Session(utc(2026, 10, 25, 0, 30), utc(2026, 10, 25, 3, 30))]
    now = utc(2026, 10, 26, 9)
    total = time_in_window(
        sessions, start=utc(2026, 10, 25, 0), end=now, now=now
    )
    assert total == timedelta(hours=4)


@test
def session_across_dst_start_is_true_elapsed():
    # 00:30 GMT to 03:30 BST: the clocks skip 01:00 to 02:00.
    sessions = [Session(utc(2026, 3, 29, 0, 30), utc(2026, 3, 29, 3, 30))]
    now = utc(2026, 3, 30, 9)
    total = time_in_window(
        sessions, start=utc(2026, 3, 29, 0), end=now, now=now
    )
    assert total == timedelta(hours=2)


@test
def prev_month_across_dst_end_is_true_elapsed():
    # Both window ends are local period starts, an hour apart in offset.
    now = utc(2026, 11, 2, 9)
    timeline = Timeline((Session(utc(2026, 9, 30, 23), utc(2026, 11, 1, 1)),))
    result = totals(timeline, now, LONDON)
    assert result.prev_month_total == timedelta(days=31, hours=1)


@test
def totals_for_readme_example():
    now = utc(2026, 10, 1, 10, 23, 45)
    timeline = Timeline(
        (
            # 8h, prev month only
            Session(utc(2026, 9, 2, 9), utc(2026, 9, 2, 17)),
            # 8h, week + prev month
            Session(utc(2026, 9, 28, 9), utc(2026, 9, 28, 17)),
            Session(utc(2026, 9, 29, 9), utc(2026, 9, 29, 17)),
            Session(utc(2026, 9, 30, 9), utc(2026, 9, 30, 17)),
            Session(utc(2026, 10, 1, 9), None),
        )
    )
    result = totals(timeline, now, LONDON)
    assert result.week_total == timedelta(hours=25, minutes=23, seconds=45)
    assert result.month_total == timedelta(hours=1, minutes=23, seconds=45)
    assert result.prev_month_total == timedelta(hours=32)


@test
def totals_carry_the_period_starts_used():
    now = utc(2026, 10, 29, 9)  # GMT day; the month began in BST
    result = totals(Timeline(), now, LONDON)
    assert result.month_start == utc(2026, 10, 1, 0)
    assert result.prev_month_start == utc(2026, 9, 1, 0)
    assert result.week_total == timedelta(0)


@test
def totals_period_starts_wrap_the_year():
    now = utc(2026, 1, 2, 9)  # Friday
    result = totals(Timeline(), now, LONDON)
    assert result.month_start == utc(2026, 1, 1, 0)
    assert result.prev_month_start == utc(2025, 12, 1, 0)
