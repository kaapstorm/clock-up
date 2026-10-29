import io
from contextlib import redirect_stdout
from pathlib import Path

from testsweet import params, test

from clock_up.__main__ import data_path, main
from clock_up.tests._helpers import LONDON, dt, temp_log


def _run(argv, now, path):
    out, err = io.StringIO(), io.StringIO()
    code = main(argv, now=now, tz=LONDON, path=path, stdout=out, stderr=err)
    return code, out.getvalue(), err.getvalue()


@test
@params(
    [
        ({'CLOCK_UP_FILE': '/x/y.log'}, Path('/x/y.log')),
        ({'XDG_DATA_HOME': '/xdg'}, Path('/xdg/clock-up/clock.log')),
        ({}, Path.home() / '.local' / 'share' / 'clock-up' / 'clock.log'),
    ]
)
def resolves_data_path(environ, expected):
    path = data_path(environ)
    assert path == expected


@test
def version_prints_and_exits_zero():
    # argparse writes --version to sys.stdout, not main()'s stdout seam.
    out = io.StringIO()
    code = None
    with redirect_stdout(out):
        try:
            main(['--version'])
        except SystemExit as exc:
            code = exc.code
    text = out.getvalue()
    assert code == 0
    assert text.startswith('clk ')
    assert text.endswith('\n')


@test
def status_with_no_data_directory():
    with temp_log() as path:
        missing = path.parent / 'nope' / 'clock.log'
        code, out, err = _run([], dt(2026, 10, 1, 9), missing)
    assert code == 0
    assert out == 'Never clocked in\n'
    assert err == ''


@test
def readme_walkthrough():
    with temp_log() as path:
        code1, out1, _ = _run(['in'], dt(2026, 10, 1, 9), path)
        code2, out2, _ = _run([], dt(2026, 10, 1, 10, 23, 45), path)
        code3, out3, _ = _run(['out'], dt(2026, 10, 1, 17), path)
        text = path.read_text()
    assert code1 == 0
    assert out1 == 'Clocked in on Thu 2026-10-01 at 09:00:00 BST\n'
    assert code2 == 0
    assert out2.startswith(
        'Clocked in for 01:23:45\nClocked in since 09:00:00 BST today\n\n'
    )
    assert code3 == 0
    assert out3 == 'Clocked out on Thu 2026-10-01 at 17:00:00 BST\n'
    assert (
        text
        == 'in  2026-10-01T09:00:00+01:00\nout 2026-10-01T17:00:00+01:00\n'
    )


@test
def forgot_to_clock_out_walkthrough():
    # Follows the README: Thursday's session, then Friday's, whose
    # clock-out, second clock-in and second clock-out are only entered
    # on Saturday.
    now = dt(2026, 10, 3, 9)
    with temp_log() as path:
        _run(['in'], dt(2026, 10, 1, 9), path)
        _run(['out'], dt(2026, 10, 1, 17), path)
        _run(['in'], dt(2026, 10, 2, 9), path)
        code1, out1, _ = _run(
            ['out', '--since', '2026-10-02 18:00'], now, path
        )
        code2, out2, _ = _run(['in', '--since', '21:00'], now, path)
        code3, out3, _ = _run(
            ['out', '--since', '2026-10-02 23:30'], now, path
        )
        code4, out4, _ = _run([], now, path)
    assert code1 == 0
    assert out1 == 'Clocked out on Fri 2026-10-02 at 18:00:00 BST\n'
    assert code2 == 0
    assert out2 == 'Clocked in on Fri 2026-10-02 at 21:00:00 BST\n'
    assert code3 == 0
    assert out3 == 'Clocked out on Fri 2026-10-02 at 23:30:00 BST\n'
    assert code4 == 0
    assert out4.startswith(
        'Clocked out for 09:30:00\nClocked out since 23:30:00 BST yesterday\n'
    )


@test
@params(
    [
        (['in'], 'Already clocked in since 09:00:00 BST today\n'),
        (
            ['in', '--since', '08:30'],
            'Already clocked in since 09:00:00 BST today\n',
        ),
        (
            ['out', '--since', '08:00'],
            '--since must be after the last event, 2026-10-01 09:00:00 BST\n',
        ),
        (['out', '--since', 'noon'], "Cannot parse --since: 'noon'\n"),
        (['out', '--since', ''], "Cannot parse --since: ''\n"),
        (
            ['out', '--since', '2026-10-02 09:00'],
            '--since must be in the past\n',
        ),
    ]
)
def refuses_and_writes_nothing(argv, message):
    now = dt(2026, 10, 1, 12)
    with temp_log() as path:
        _run(['in'], dt(2026, 10, 1, 9), path)
        before = path.read_text()
        code, out, err = _run(argv, now, path)
        after = path.read_text()
    assert code == 1
    assert out == ''
    assert err == message
    assert after == before


@test
def out_when_never_clocked_in():
    with temp_log() as path:
        code, _, err = _run(['out'], dt(2026, 10, 1, 9), path)
        exists = path.exists()
    assert code == 1
    assert err == 'Not clocked in\n'
    assert not exists


@test
def bad_data_file_is_reported():
    with temp_log() as path:
        path.write_text('garbage\n')
        code, _, err = _run([], dt(2026, 10, 1, 9), path)
    assert code == 1
    assert err == (
        f'{path}:1: cannot parse \'garbage\': expected "<kind> <timestamp>"\n'
    )


@test
def in_twice_in_same_second_is_already_clocked_in():
    now = dt(2026, 10, 1, 9)
    with temp_log() as path:
        _run(['in'], now, path)
        before = path.read_text()
        code, out, err = _run(['in'], now, path)
        after = path.read_text()
    assert code == 1
    assert out == ''
    assert err == 'Already clocked in since 09:00:00 BST today\n'
    assert after == before


@test
def out_in_same_second_does_not_mention_since():
    now = dt(2026, 10, 1, 9)
    with temp_log() as path:
        _run(['in'], now, path)
        before = path.read_text()
        code, out, err = _run(['out'], now, path)
        after = path.read_text()
    assert code == 1
    assert out == ''
    assert err == 'Last event 09:00:00 BST today is not before now\n'
    assert after == before


@test
def out_after_future_event_does_not_mention_since():
    with temp_log() as path:
        path.write_text('in 2026-10-02T09:00:00+01:00\n')
        code, _, err = _run(['out'], dt(2026, 10, 1, 9), path)
    assert code == 1
    assert (
        err == 'Last event 09:00:00 BST on Fri 2026-10-02 is not before now\n'
    )


@test
def non_alternating_file_names_both_lines():
    with temp_log() as path:
        path.write_text(
            '# hand-edited\n'
            'in  2026-10-02T09:00:00+01:00\n'
            'out 2026-10-01T17:00:00+01:00\n'
            'in  2026-10-01T09:00:00+01:00\n'
            'in  2026-10-01T18:00:00+01:00\n'
        )
        code, _, err = _run([], dt(2026, 10, 2, 12), path)
    assert code == 1
    assert err == (
        f'{path}:2: in at 2026-10-02 09:00:00 BST follows in at line 5\n'
    )


@test
def data_path_that_is_a_directory_is_reported():
    with temp_log() as path:
        path.mkdir()
        code, out, err = _run([], dt(2026, 10, 1, 9), path)
    assert code == 1
    assert out == ''
    assert err == f'{path}: Is a directory\n'


@test
def undecodable_data_file_is_reported():
    with temp_log() as path:
        path.write_bytes(b'\xff')
        code, out, err = _run([], dt(2026, 10, 1, 9), path)
    assert code == 1
    assert out == ''
    assert err.startswith(f'{path}: ')
    assert "'utf-8' codec can't decode byte 0xff" in err


@test
@params([([],), (['in'],)])
def data_path_under_a_regular_file_is_reported(argv):
    with temp_log() as path:
        path.write_text('')
        blocked = path / 'clock.log'  # parent is a regular file
        code, out, err = _run(argv, dt(2026, 10, 1, 9), blocked)
    assert code == 1
    assert out == ''
    assert err == f'{blocked}: Not a directory\n'
