from datetime import datetime, timedelta, tzinfo

TIME_FORMAT = '%H:%M:%S %Z'
DATE_FORMAT = '%a %Y-%m-%d'


def format_duration(td: timedelta) -> str:
    """Format as HH:MM:SS, with unbounded hours."""
    minutes, seconds = divmod(int(td.total_seconds()), 60)
    hours, minutes = divmod(minutes, 60)
    return f'{hours:02d}:{minutes:02d}:{seconds:02d}'


def format_stamp(at: datetime, tz: tzinfo) -> str:
    return at.astimezone(tz).strftime(f'%Y-%m-%d {TIME_FORMAT}')


def time_phrase(at: datetime, now: datetime, tz: tzinfo) -> str:
    local = at.astimezone(tz)
    days_ago = (now.astimezone(tz).date() - local.date()).days
    clock = local.strftime(TIME_FORMAT)
    if days_ago == 0:
        return f'{clock} today'
    if days_ago == 1:
        return f'{clock} yesterday'
    return f'{clock} on {local.strftime(DATE_FORMAT)}'
