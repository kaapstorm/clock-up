import os
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, tzinfo
from pathlib import Path
from typing import cast, get_args

from clock_up._errors import BadLine, IoFailure, Kind


@dataclass(frozen=True, order=True)
class Event:
    at: datetime
    kind: Kind
    # 1-based line number in the log file; 0 for events not read from it.
    lineno: int = field(compare=False, default=0)


def parse_line(line: str) -> Event | None:
    """Parse one log line; None for blank and comment lines."""
    stripped = line.strip()
    if not stripped or stripped.startswith('#'):
        return None
    fields = stripped.split()
    if len(fields) != 2:
        raise ValueError('expected "<kind> <timestamp>"')
    kind, stamp = fields
    if kind not in get_args(Kind):
        raise ValueError('unknown kind')
    at = datetime.fromisoformat(stamp)
    if at.tzinfo is None:
        raise ValueError('timestamp has no UTC offset')
    return Event(at, cast(Kind, kind))


def format_line(event: Event, tz: tzinfo) -> str:
    # Write local time with its offset, so the file reads naturally when
    # edited by hand.
    stamp = event.at.astimezone(tz).isoformat(timespec='seconds')
    return f'{event.kind:<3} {stamp}'


def _io_error(path: Path, exc: OSError | UnicodeDecodeError) -> IoFailure:
    if isinstance(exc, OSError):
        # The OS names the file it failed on, which may be a parent of
        # the log, such as a regular file where a directory should be.
        where = Path(exc.filename) if exc.filename else path
        return IoFailure(path=where, reason=exc.strerror or str(exc))
    return IoFailure(path=path, reason=str(exc))


def load(path: Path) -> list[Event]:
    """Read the log, sorted, with each ``at`` converted to UTC."""
    events = []
    try:
        text = path.read_text(encoding='utf-8')
    except FileNotFoundError:
        return []  # no log yet
    except (OSError, UnicodeDecodeError) as exc:
        raise _io_error(path, exc) from None
    # Split on '\n' only, so line numbers match an editor's; strip() in
    # parse_line tolerates CRLF.
    for lineno, line in enumerate(text.split('\n'), start=1):
        try:
            event = parse_line(line)
            if event is None:
                continue
            at = event.at.astimezone(UTC)
        except ValueError as exc:
            raise BadLine(
                path=path, lineno=lineno, line=line, reason=str(exc)
            ) from None
        except OverflowError:
            raise BadLine(
                path=path,
                lineno=lineno,
                line=line,
                reason='timestamp out of range',
            ) from None
        events.append(replace(event, at=at, lineno=lineno))
    return sorted(events)


def append(path: Path, event: Event, tz: tzinfo) -> None:
    """Append ``event`` to the log, creating it private if it is new.

    The log shows when its owner works, so the log's own directory is
    created 0o700 if it is new (missing parents get default
    permissions), and the file 0o600 if it is new. Existing files and
    directories are left alone.
    """
    try:
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        prefix = ''
        # A file edited by hand may not end with a newline; start a new
        # line rather than run on from its last one.
        if path.exists() and path.stat().st_size > 0:
            with path.open('rb') as f:
                f.seek(-1, os.SEEK_END)
                if f.read(1) != b'\n':
                    prefix = '\n'
        flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
        fd = os.open(path, flags, 0o600)
        with os.fdopen(fd, 'a', encoding='utf-8') as f:
            f.write(prefix + format_line(event, tz) + '\n')
    except OSError as exc:
        raise _io_error(path, exc) from None
