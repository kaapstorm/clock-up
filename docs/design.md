Clock Up design notes
=====================

These notes explain why `clk` behaves as it does, for anyone changing
the code or wondering about a choice.


Scope
-----

`clk` tracks one person's working time on one machine. You clock in,
you clock out, and you ask how much you have worked this week, this
month and last month. There are no projects, tags or clients, and the
status display is the only report. Keeping the tool this small is the
point: heavier time trackers get in the way of the work they measure.

The one correction built into the CLI is `--since`, for the forgotten
clock-in or clock-out, because that is the mistake manual tracking
always produces. Anything else is fixed by editing the data file.
Running two `clk` commands at the same moment is out of scope; nothing
locks the file, although the next read reports any damage this causes.


The data file
-------------

The log is a UTF-8 text file with one event per line: `in` or `out`,
then an ISO 8601 timestamp with its UTC offset, such as
`in  2026-10-01T09:00:00+01:00`. The offset makes every line an exact
instant, whatever the time zone or DST period. `clk` writes local time
with that offset, rather than UTC, so the file reads naturally when you
open it in an editor. Blank lines and lines starting with `#` are
ignored, so you can annotate it.

The file is append-only, and the reader sorts events by time. That is
what lets `--since` be a single appended line: a back-dated event can
go at the end of the file and still land in the right place. A write
never rewrites the file, and happens only after every check has
passed, so a failed command leaves the file exactly as it was.

Why not SQLite? Everything `clk` does is "read all events, sort, add
up", and a decade of twice-daily events is a few thousand lines that
parse in milliseconds. A database would bring concurrency and indexes
the tool does not need, and cost what matters more: a file you can
read, fix with an editor, diff and keep in version control.


The timeline rules
------------------

Sorted by time, events must go `in`, `out`, `in`, `out` and so on,
starting with `in`, with strictly increasing timestamps. A file that
breaks this is reported with its path and line number, never repaired
silently, because a doubled clock-in would make every later total
wrong without anyone noticing. A command that would break the rules is
refused with a message and exit code 1, and nothing is written.

`--since` must be after the last recorded event and not in the future.
That is the only window a single new event can occupy: inserted
anywhere earlier, it would sit between an `in` and an `out` (or an
`out` and an `in`) and create a double. Splitting or moving a closed
session therefore needs two edits, which is a job for an editor.

When a command is both the wrong kind and at the wrong time, such as
`clk in --since 08:30` while clocked in since 09:00, the kind is
reported, because no choice of time could fix it.


Time zones
----------

Inside the program every instant is a UTC `datetime`. Local time
appears only at the edges: when parsing `--since`, when building the
start of the week and month, and when displaying a time. This keeps the
arithmetic free of DST surprises.

The local zone must carry real DST rules. `datetime.now().astimezone()`
gives only today's fixed offset, which is an hour wrong for any date in
the other DST period: on a GMT day in late October it would put the
start of the month an hour late and misplace a `--since` date from a
BST week. So `clk` looks up the zone in this order and uses the first
that names a known zone: the `TZ` environment variable (with or without
a leading `:`), then the zone that `/etc/localtime` links to. Only if
both fail does it fall back to the fixed offset, which is still right
for durations and for anything in the current DST period.

During the repeated hour when DST ends, a wall-clock time could mean
either of two instants; `clk` takes the first and does not treat it as
an error. A time in the skipped hour when DST starts is read with the
offset from before the change, so in `Europe/London` 01:30 on the
spring-forward day becomes 02:30 BST. Durations are differences
between instants, so a session across a DST change counts its true
elapsed time.


The status display
------------------

The week starts on Sunday at 00:00 local time. The open session, if
any, counts up to now towards all three totals, so the numbers always
agree with each other. "Last month" is the whole previous calendar
month; a session that crosses a month boundary is split between the
two months. Durations are hours, minutes and seconds, with hours never
wrapped at 24, and are right-aligned to the widest value in the block.


`--since` forms
---------------

Six forms are accepted, all in local time: `HH:MM`, `HH:MM:SS`,
`YYYY-MM-DD HH:MM`, `YYYY-MM-DD HH:MM:SS`, and the last two with `T` in
place of the space. A bare time means its most recent past occurrence,
so `21:00` typed at 09:00 means 21:00 yesterday, and typed at 22:00
means 21:00 today. That matches the usual case of noticing the next
morning that you forgot. The day is stepped back on the calendar, not
by 24 hours, so the wall-clock time is kept across a DST change.

The parser also happens to accept single-digit fields such as `9:05`.
That is a side effect of the standard library parser, not a promise.


Testing approach
----------------

Only the entry point reads the clock, the environment and the default
file path. It passes `now`, the time zone and the path into everything
else, so tests supply fixed values instead of patching anything. Tests
pin exact output strings, and use dates on both sides of the March and
October DST changes in `Europe/London`. That needs the IANA time zone
database, which some systems lack, so `tzdata` is in the `dev`
dependency group.
