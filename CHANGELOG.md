Changelog
=========

Unreleased
----------

### Added

- `clk in` and `clk out` record a clock-in or clock-out at the current
  time.
- `clk` shows the open session (or the time since the last clock-out)
  and totals for this week, this month so far, and the previous month.
- `--since WHEN` on `clk in` and `clk out` backdates the event, for a
  forgotten clock-in or clock-out.
- `clk --version` prints the installed version.
- A plain-text log at `$CLOCK_UP_FILE`, else
  `$XDG_DATA_HOME/clock-up/clock.log`, else
  `~/.local/share/clock-up/clock.log`.
