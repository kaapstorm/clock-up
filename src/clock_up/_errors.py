from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

# The kinds of event in the log. Defined here rather than in _events,
# which imports this module, so that error fields can use it too.
Kind = Literal['in', 'out']


class ClockUpError(Exception):
    """A user-facing failure.

    Subclasses carry data, not text. ``_report.error_message`` is the
    one place that turns them into messages, in local time and in terms
    of what the user typed.

    The subclasses use ``eq=False``, so they stay hashable and compare
    by identity like other exceptions.
    """

    def __str__(self) -> str:
        """The repr, for developers rather than users.

        Dataclass fields do not reliably reach ``args`` (keyword-only
        fields never do), so the default ``str()`` would be empty or
        partial.
        """
        return repr(self)


@dataclass(eq=False)
class AlreadyClockedIn(ClockUpError):
    """Raised by ``clk in`` while clocked in."""

    since: datetime


@dataclass(eq=False)
class NotClockedIn(ClockUpError):
    """Raised by ``clk out`` while not clocked in."""


@dataclass(eq=False)
class InFuture(ClockUpError):
    """Raised when a new event's time is after now."""

    at: datetime


@dataclass(eq=False)
class NotAfterLast(ClockUpError):
    """Raised when a new event's time is not after the last event."""

    last: datetime


@dataclass(eq=False)
class BadSince(ClockUpError):
    """Raised when a ``--since`` value cannot be parsed."""

    text: str


@dataclass(eq=False, kw_only=True)
class BadLine(ClockUpError):
    """Raised when a log line cannot be parsed."""

    path: Path
    lineno: int
    line: str
    reason: str


@dataclass(eq=False, kw_only=True)
class StartsWithOut(ClockUpError):
    """Raised when the earliest event in the log is a clock-out."""

    path: Path
    lineno: int
    at: datetime


@dataclass(eq=False, kw_only=True)
class NotAlternating(ClockUpError):
    """Raised when an event has the same kind as the one before it."""

    path: Path
    lineno: int
    kind: Kind
    at: datetime
    previous_lineno: int


@dataclass(eq=False, kw_only=True)
class SharedTimestamp(ClockUpError):
    """Raised when two events in the log have the same time."""

    path: Path
    lineno: int
    kind: Kind
    at: datetime
    previous_kind: Kind
    previous_lineno: int


@dataclass(eq=False, kw_only=True)
class IoFailure(ClockUpError):
    """Raised when the log cannot be read or written."""

    path: Path
    reason: str
