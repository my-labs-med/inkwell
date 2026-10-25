import re
from datetime import UTC, date, datetime, timedelta

_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def utc_now():
    return datetime.now(UTC)


def iso(moment):
    return moment.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def client_day(value, now):
    today = now.date()
    if isinstance(value, str) and _DAY.match(value):
        try:
            candidate = date.fromisoformat(value)
        except ValueError:
            candidate = None
        if candidate and abs((candidate - today).days) <= 1:
            return candidate.isoformat()
    return today.isoformat()


def days_before(day, count):
    return (date.fromisoformat(day) - timedelta(days=count)).isoformat()


def streak_ending(day, active_days):
    streak = 0
    current = date.fromisoformat(day)
    while current.isoformat() in active_days:
        streak += 1
        current -= timedelta(days=1)
    return streak
