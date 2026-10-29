from collections.abc import Mapping
from datetime import UTC, datetime, time, timedelta, tzinfo
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from clock_up._errors import BadSince

_TIME_FORMATS = ('%H:%M', '%H:%M:%S')
_DATETIME_FORMATS = (
    '%Y-%m-%d %H:%M',
    '%Y-%m-%d %H:%M:%S',
    '%Y-%m-%dT%H:%M',
    '%Y-%m-%dT%H:%M:%S',
)


def parse_since(text: str, now: datetime, tz: tzinfo) -> datetime:
    """Parse a --since value, given in ``tz``, into a UTC instant."""
    for fmt in _DATETIME_FORMATS:
        try:
            naive = datetime.strptime(text, fmt)
        except ValueError:
            continue
        try:
            # Relies on fold=0: an ambiguous time takes the first instant
            # and a skipped time the earlier offset, as docs/design.md says.
            return naive.replace(tzinfo=tz).astimezone(UTC)
        except OverflowError:
            raise BadSince(text) from None
    for fmt in _TIME_FORMATS:
        try:
            parsed = datetime.strptime(text, fmt)
        except ValueError:
            continue
        return _most_recent_past(parsed.time(), now, tz)
    raise BadSince(text)


def _most_recent_past(
    time_of_day: time, now: datetime, tz: tzinfo
) -> datetime:
    """The last ``time_of_day`` in ``tz`` before ``now``, as UTC.

    That is today's if it has passed, else yesterday's. The day is
    stepped back on the calendar, not by 24 hours, so that across a DST
    change the result keeps the wall-clock time asked for.
    """
    today = now.astimezone(tz).date()
    candidate = datetime.combine(today, time_of_day, tzinfo=tz)
    if candidate.astimezone(UTC) >= now.astimezone(UTC):
        yesterday = today - timedelta(days=1)
        candidate = datetime.combine(yesterday, time_of_day, tzinfo=tz)
    return candidate.astimezone(UTC)


def local_zone(
    environ: Mapping[str, str],
    localtime: Path = Path('/etc/localtime'),
) -> tzinfo:
    """The user's time zone, with real DST rules where possible.

    Tries ``$TZ`` (an IANA key, optionally ':'-prefixed), then the key
    that ``/etc/localtime`` links to. Only then falls back to the
    current fixed offset, which is wrong for dates in the other DST
    period and so misplaces week and month boundaries.
    """
    key = environ.get('TZ', '').removeprefix(':')
    if key and (zone := _zone_or_none(key)):
        return zone
    key = _linked_key(localtime)
    if key and (zone := _zone_or_none(key)):
        return zone
    fallback = datetime.now().astimezone().tzinfo
    if fallback is None:  # never true; narrows the type for the checker
        raise RuntimeError('Cannot find the local time zone')
    return fallback


def _linked_key(localtime: Path) -> str | None:
    """The zone key that ``localtime`` links to, if it is such a link."""
    try:
        if not localtime.is_symlink():
            return None
        target = localtime.resolve().as_posix()
    except (OSError, RuntimeError):  # a loop is RuntimeError before 3.13
        return None
    _, found, key = target.rpartition('/zoneinfo/')
    return key if found else None


def _zone_or_none(key: str) -> ZoneInfo | None:
    try:
        return ZoneInfo(key)
    except (ZoneInfoNotFoundError, ValueError, OSError):
        return None
