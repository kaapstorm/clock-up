import tempfile
from collections.abc import Generator, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

LONDON = ZoneInfo('Europe/London')
LOG = Path('clock.log')


def dt(y: int, m: int, d: int, H: int, M: int = 0, S: int = 0) -> datetime:
    return datetime(y, m, d, H, M, S, tzinfo=LONDON)


def utc(y: int, m: int, d: int, H: int, M: int = 0, S: int = 0) -> datetime:
    """London wall-clock time as a UTC instant, as the timeline uses."""
    return dt(y, m, d, H, M, S).astimezone(UTC)


@contextmanager
def temp_log() -> Generator[Path]:
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / 'clock.log'


def assert_raised_like(
    excs: Sequence[BaseException], expected: BaseException
) -> None:
    """Assert that ``excs`` holds one exception like ``expected``.

    Like means the same type and the same instance attributes.
    """
    count = len(excs)
    assert count == 1
    exc_type = type(excs[0])
    fields = vars(excs[0])
    assert exc_type is type(expected)
    assert fields == vars(expected)
