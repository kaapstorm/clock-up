import argparse
import os
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, tzinfo
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import TextIO, get_args

from clock_up._errors import ClockUpError
from clock_up._events import Event, Kind, append, load
from clock_up._report import confirmation, error_message, status
from clock_up._timeline import check_append, validate
from clock_up._when import local_zone, parse_since


def data_path(environ: Mapping[str, str]) -> Path:
    if environ.get('CLOCK_UP_FILE'):
        return Path(environ['CLOCK_UP_FILE'])
    base = environ.get('XDG_DATA_HOME')
    root = Path(base) if base else Path.home() / '.local' / 'share'
    return root / 'clock-up' / 'clock.log'


def _version() -> str:
    try:
        return version('clock-up')
    except PackageNotFoundError:  # running from a tree that isn't installed
        return 'unknown'


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='clk',
        description='Track your working time. With no command, show status.',
    )
    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {_version()}',
    )
    commands = parser.add_subparsers(dest='command')
    for name in get_args(Kind):
        sub = commands.add_parser(name, help=f'clock {name}')
        sub.add_argument(
            '--since',
            metavar='WHEN',
            help=(
                'when it happened, in local time: HH:MM[:SS] (its most '
                'recent past occurrence) or YYYY-MM-DD HH:MM[:SS] '
                '(or with T)'
            ),
        )
    parser.set_defaults(since=None)  # bare clk has no --since
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    now: datetime | None = None,
    tz: tzinfo | None = None,
    path: Path | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Run clk. The keyword-only parameters are seams for tests."""
    args = _parser().parse_args(argv)
    since_given = args.since is not None
    if tz is None:
        tz = local_zone(os.environ)
    if now is None:
        # The log stores whole seconds; keep now comparable with what
        # load() reads back.
        now = datetime.now(tz).replace(microsecond=0)
    now = now.astimezone(UTC)
    if path is None:
        path = data_path(os.environ)
    out = stdout if stdout is not None else sys.stdout
    err = stderr if stderr is not None else sys.stderr
    try:
        timeline = validate(load(path), path)
        if args.command is None:
            print(status(timeline, now, tz), file=out)
        else:
            kind = args.command
            at = parse_since(args.since, now, tz) if since_given else now
            check_append(timeline, kind, at, now)
            append(path, Event(at, kind), tz)
            print(confirmation(kind, at, tz), file=out)
    except ClockUpError as exc:
        err.write(error_message(exc, now, tz, since_given) + '\n')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
