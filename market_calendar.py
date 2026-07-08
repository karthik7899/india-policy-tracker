"""NSE trading-day calendar, used only to gate the *daily* scheduled cron so
it doesn't burn a run (and email stale/unchanged prices) on a day the
exchange never opened. The weekly Saturday digest and manual
workflow_dispatch runs deliberately bypass this — see daily-brief.yml.

Holiday dates are maintained by hand and must be refreshed every year from
NSE's published trading-holiday circular (nseindia.com > Market Timings &
Holidays). Deliberately conservative: an omitted holiday just means one
extra run with unchanged prices, but a wrongly-added date would silently
skip a real trading day, so when a date can't be corroborated across
multiple sources it is left out rather than guessed.
"""

import datetime

NSE_HOLIDAYS_2026 = {
    "2026-01-26",  # Republic Day
    "2026-03-03",  # Holi
    "2026-03-26",  # Shri Ram Navami
    "2026-03-31",  # Shri Mahavir Jayanti
    "2026-04-03",  # Good Friday
    "2026-04-14",  # Dr. Baba Saheb Ambedkar Jayanti
    "2026-05-01",  # Maharashtra Day
    "2026-05-28",  # Bakri Id
    "2026-06-26",  # Muharram
    "2026-08-15",  # Independence Day (also a Saturday)
    "2026-09-14",  # Ganesh Chaturthi
    "2026-10-02",  # Mahatma Gandhi Jayanti
    "2026-11-08",  # Diwali Laxmi Pujan (also a Sunday)
    "2026-12-25",  # Christmas
}


def is_trading_day(date):
    """True if ``date`` (a ``datetime.date``) is a normal NSE trading day —
    not a Saturday/Sunday and not a known exchange holiday."""
    if date.weekday() >= 5:  # 5=Saturday, 6=Sunday
        return False
    return date.isoformat() not in NSE_HOLIDAYS_2026


if __name__ == "__main__":
    print(is_trading_day(datetime.date.today()))
