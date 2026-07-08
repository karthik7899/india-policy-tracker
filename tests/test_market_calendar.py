import datetime
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from market_calendar import is_trading_day  # noqa: E402


def test_weekday_non_holiday_is_trading_day():
    assert is_trading_day(datetime.date(2026, 7, 9)) is True  # Thursday


def test_saturday_and_sunday_are_not_trading_days():
    assert is_trading_day(datetime.date(2026, 7, 4)) is False  # Saturday
    assert is_trading_day(datetime.date(2026, 7, 5)) is False  # Sunday


def test_known_holiday_is_not_a_trading_day():
    assert is_trading_day(datetime.date(2026, 1, 26)) is False  # Republic Day (Mon)
    assert is_trading_day(datetime.date(2026, 12, 25)) is False  # Christmas (Fri)


def test_day_after_holiday_is_a_trading_day():
    assert is_trading_day(datetime.date(2026, 1, 27)) is True
