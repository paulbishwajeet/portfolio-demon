from datetime import datetime, date
import pytz

ET = pytz.timezone("US/Eastern")


def now_et() -> datetime:
    return datetime.now(ET)


def today_et() -> date:
    return now_et().date()


def is_weekday(d: date = None) -> bool:
    d = d or today_et()
    return d.weekday() < 5


def is_trading_day(d: date = None) -> bool:
    d = d or today_et()
    if not is_weekday(d):
        return False
    # Major US market holidays (approximate — covers most years)
    month_day = (d.month, d.day)
    fixed_holidays = {
        (1, 1),   # New Year's Day
        (7, 4),   # Independence Day
        (12, 25), # Christmas Day
    }
    if month_day in fixed_holidays:
        return False
    return True


def iso_now() -> str:
    return now_et().isoformat()
