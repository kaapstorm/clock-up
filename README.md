Clock Up
========

A minimalist command line utility for time tracking.

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

Forgot to clock out, or in?

```shell
$ clk out --since '2026-09-30 18:00'
Clocked out on Wed 2026-09-30 at 18:00:00 BST

$ clk in --since 21:00
Clocked in on Wed 2026-09-30 at 21:00:00 BST
```

