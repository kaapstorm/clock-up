Clock Up
========

A minimalist command line utility for time tracking.

### Installing

```shell
uv tool install clock-up
```

or

```shell
pip install clock-up
```

or, from a checkout:

```shell
uv tool install .
```

### Usage

Clock in at the start of the work day:

```shell
$ clk in
Clocked in on Thu 2026-10-01 at 09:00:00 BST
```

Clock out at the end of the work day:

```shell
$ clk out
Clocked out on Thu 2026-10-01 at 17:00:00 BST
```

Show current status:

```shell
$ clk
Clocked in for 01:23:45
Clocked in since 09:00:00 BST today

 24:00:00 clocked this week
 01:23:45 clocked so far in Oct 2026
120:00:00 clocked in Sep 2026
```

The totals are for this week (weeks start on Sunday), this month so far,
and the whole of last month.

Forgot to clock out, or in? Say you clocked in on Friday morning,
forgot to clock out at 18:00, and went back to work from 21:00 to
23:30 without clocking in or out. On Saturday morning:

```shell
$ clk out --since '2026-10-02 18:00'
Clocked out on Fri 2026-10-02 at 18:00:00 BST

$ clk in --since 21:00
Clocked in on Fri 2026-10-02 at 21:00:00 BST

$ clk out --since '2026-10-02 23:30'
Clocked out on Fri 2026-10-02 at 23:30:00 BST
```

A bare `HH:MM` means its most recent past occurrence, so `21:00` typed
at 09:00 means 21:00 yesterday.

`--since` must be after your last recorded event and not in the future;
to fix anything earlier, edit the data file (see
[Data file](#data-file)).

### Data file

Data lives in `$CLOCK_UP_FILE`, else `$XDG_DATA_HOME/clock-up/clock.log`,
else `~/.local/share/clock-up/clock.log`. It is a plain text file you can
edit.

One event per line, `in` or `out` and then a timestamp:

```
in  2026-10-01T09:00:00+01:00
out 2026-10-01T17:00:00+01:00
```

When editing it by hand:

- Every timestamp needs a UTC offset, such as `+01:00` or `Z`.
- `in` and `out` must alternate, starting with `in`, once the lines are
  sorted by time.
- No two events may have the same timestamp.
- Lines may be in any order in the file; `clk` sorts them.
- Blank lines and lines starting with `#` are ignored.

Running two `clk` commands at the same moment is not supported.

### Design

Design notes: [docs/design.md](https://github.com/kaapstorm/clock-up/blob/main/docs/design.md).
