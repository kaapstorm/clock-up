import os
import stat
from datetime import UTC

from testsweet import catch_exceptions, params, skip, test

from clock_up._errors import BadLine, IoFailure
from clock_up._events import Event, append, format_line, load, parse_line
from clock_up.tests._helpers import (
    LONDON,
    assert_raised_like,
    dt,
    temp_log,
    utc,
)


@test
@params(
    [
        ('in 2026-10-01T09:00:00+01:00', Event(dt(2026, 10, 1, 9), 'in')),
        ('out  2026-10-01T17:00:00+01:00', Event(dt(2026, 10, 1, 17), 'out')),
        ('in\t2026-10-01T09:00:00+01:00', Event(dt(2026, 10, 1, 9), 'in')),
        ('', None),
        ('   ', None),
        ('# a comment', None),
    ]
)
def parses_line(line, expected):
    event = parse_line(line)
    assert event == expected


@test
@params(
    [
        ('in 2026-10-01T09:00:00',),  # no UTC offset
        ('in',),
        ('sideways 2026-10-01T09:00:00+01:00',),
        ('in 2026-10-01T09:00:00+01:00 extra',),
        ('in not-a-date',),
    ]
)
def rejects_bad_line(line):
    with catch_exceptions() as excs:
        parse_line(line)
    assert_raised_like(excs, ValueError())


@test
def formats_line_aligned():
    line_in = format_line(Event(dt(2026, 10, 1, 9), 'in'), LONDON)
    line_out = format_line(Event(dt(2026, 10, 1, 17), 'out'), LONDON)
    assert line_in == 'in  2026-10-01T09:00:00+01:00'
    assert line_out == 'out 2026-10-01T17:00:00+01:00'


@test
@params(
    [
        (utc(2026, 10, 1, 9), 'in  2026-10-01T09:00:00+01:00'),  # BST
        (utc(2026, 10, 26, 9), 'in  2026-10-26T09:00:00+00:00'),  # GMT
    ]
)
def formats_utc_instant_in_local_time(at, expected):
    line = format_line(Event(at, 'in'), LONDON)
    assert line == expected


@test
def formats_line_at_seconds_precision():
    at = dt(2026, 10, 1, 9).replace(microsecond=999999)
    line = format_line(Event(at, 'in'), LONDON)
    assert line == 'in  2026-10-01T09:00:00+01:00'


@test
def load_missing_file_is_empty():
    with temp_log() as path:
        events = load(path)
    assert events == []


@test
def load_sorts_and_ignores_comments():
    text = (
        '# started tracking\n'
        'in  2026-10-01T09:00:00+01:00\n'
        '\n'
        'out 2026-09-30T18:00:00+01:00\n'
        'in  2026-09-30T09:00:00+01:00\n'
    )
    with temp_log() as path:
        path.write_text(text)
        events = load(path)
    kinds = [e.kind for e in events]
    starts = [e.at for e in events]
    assert kinds == ['in', 'out', 'in']
    assert starts == [
        dt(2026, 9, 30, 9),
        dt(2026, 9, 30, 18),
        dt(2026, 10, 1, 9),
    ]


@test
def load_tolerates_crlf_and_missing_final_newline():
    with temp_log() as path:
        path.write_bytes(
            b'in 2026-10-01T09:00:00+01:00\r\nout 2026-10-01T17:00:00+01:00'
        )
        events = load(path)
    count = len(events)
    assert count == 2


@test
def load_reports_bad_line_number():
    with temp_log() as path:
        path.write_text('in 2026-10-01T09:00:00+01:00\n\nxyz\n')
        with catch_exceptions() as excs:
            load(path)
        expected = BadLine(
            path=path,
            lineno=3,
            line='xyz',
            reason='expected "<kind> <timestamp>"',
        )
    assert_raised_like(excs, expected)


@test
@params(
    [
        ('in 0001-01-01T00:00:00+14:00',),
        ('in 9999-12-31T23:00:00-05:00',),
    ]
)
def load_reports_out_of_range_timestamp(line):
    with temp_log() as path:
        path.write_text(line + '\n')
        with catch_exceptions() as excs:
            load(path)
        expected = BadLine(
            path=path, lineno=1, line=line, reason='timestamp out of range'
        )
    assert_raised_like(excs, expected)


@test
def load_numbers_lines_as_an_editor_does():
    # A form feed is a line break to splitlines() but not to an editor.
    with temp_log() as path:
        path.write_text(
            'in 2026-10-01T09:00:00+01:00 \x0c\n'
            'out 2026-10-01T17:00:00+01:00\n'
        )
        events = load(path)
    linenos = [e.lineno for e in events]
    assert linenos == [1, 2]


@test
def append_creates_directories_and_round_trips():
    with temp_log() as path:
        nested = path.parent / 'a' / 'b' / 'clock.log'
        append(nested, Event(dt(2026, 10, 1, 9), 'in'), LONDON)
        append(nested, Event(dt(2026, 10, 1, 17), 'out'), LONDON)
        text = nested.read_text()
        events = load(nested)
    assert (
        text
        == 'in  2026-10-01T09:00:00+01:00\nout 2026-10-01T17:00:00+01:00\n'
    )
    assert events == [
        Event(dt(2026, 10, 1, 9), 'in'),
        Event(dt(2026, 10, 1, 17), 'out'),
    ]


@test
def append_starts_new_line_after_missing_newline():
    with temp_log() as path:
        path.write_text('in 2026-10-01T09:00:00+01:00')
        append(path, Event(dt(2026, 10, 1, 17), 'out'), LONDON)
        text = path.read_text()
    assert (
        text == 'in 2026-10-01T09:00:00+01:00\nout 2026-10-01T17:00:00+01:00\n'
    )


@test
def load_reports_unreadable_path():
    with temp_log() as path:
        path.mkdir()
        with catch_exceptions() as excs:
            load(path)
        expected = IoFailure(path=path, reason='Is a directory')
    assert_raised_like(excs, expected)


@test
def load_reports_undecodable_file():
    with temp_log() as path:
        path.write_bytes(b'\xff\n')
        with catch_exceptions() as excs:
            load(path)
    count = len(excs)
    exc_type = type(excs[0])
    fields = vars(excs[0])
    assert count == 1
    assert exc_type is IoFailure
    assert fields['path'] == path
    assert 'utf-8' in fields['reason']


@test
def append_names_the_file_blocking_its_directory():
    with temp_log() as path:
        path.write_text('')
        blocked = path / 'clock.log'  # parent is a regular file
        with catch_exceptions() as excs:
            append(blocked, Event(dt(2026, 10, 1, 9), 'in'), LONDON)
        expected = IoFailure(path=path, reason='File exists')
    assert_raised_like(excs, expected)


@test
def load_reports_regular_file_as_parent():
    with temp_log() as path:
        path.write_text('')
        blocked = path / 'clock.log'  # parent is a regular file
        with catch_exceptions() as excs:
            load(blocked)
        expected = IoFailure(path=blocked, reason='Not a directory')
    assert_raised_like(excs, expected)


# os.geteuid does not exist on Windows, where file modes are not
# meaningful either.
IS_ROOT = getattr(os, 'geteuid', lambda: -1)() == 0


@test
@skip(
    condition=IS_ROOT,
    reason='file modes are not meaningful when run as root',
)
def append_creates_private_file_and_directory():
    with temp_log() as path:
        log = path.parent / 'clock-up' / 'clock.log'
        append(log, Event(dt(2026, 10, 1, 9), 'in'), LONDON)
        file_mode = stat.S_IMODE(log.stat().st_mode)
        dir_mode = stat.S_IMODE(log.parent.stat().st_mode)
    assert file_mode == 0o600
    assert dir_mode == 0o700


@test
def append_keeps_mode_of_existing_file():
    with temp_log() as path:
        path.write_text('')
        path.chmod(0o644)
        append(path, Event(dt(2026, 10, 1, 9), 'in'), LONDON)
        file_mode = stat.S_IMODE(path.stat().st_mode)
    assert file_mode == 0o644


@test
def load_returns_utc_instants():
    with temp_log() as path:
        path.write_text('in 2026-10-01T09:00:00+01:00\n')
        events = load(path)
    zone = events[0].at.tzinfo
    assert zone is UTC
    assert events == [Event(dt(2026, 10, 1, 9), 'in')]


@test
@skip(
    condition=IS_ROOT,
    reason='root ignores directory permissions',
)
def load_reports_unreadable_parent_directory():
    with temp_log() as path:
        path.parent.chmod(0o000)
        try:
            with catch_exceptions() as excs:
                load(path)
        finally:
            path.parent.chmod(0o700)
        expected = IoFailure(path=path, reason='Permission denied')
    assert_raised_like(excs, expected)
