from datetime import datetime, timedelta, timezone


def india_today():
    """Calendar date in India, independent of the server's timezone."""
    return datetime.now(timezone(timedelta(hours=5, minutes=30))).date()
