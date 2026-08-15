"""Tests for delivery percentage (providers/nse_delivery.py).

The distinction this module exists to draw is between volume and delivery,
so the cases below are mostly about not conflating them — and about the two
ways this pipeline has already lost data of exactly this shape: writing to a
dict the Screener rebuild later replaces, and attaching a field the Pydantic
model does not declare.
"""

import asyncio
import datetime

import pytest

from providers import nse_delivery as nd

CSV = """SYMBOL,SERIES,DATE1,PREV_CLOSE,OPEN_PRICE,HIGH_PRICE,LOW_PRICE,LAST_PRICE,CLOSE_PRICE,AVG_PRICE,TTL_TRD_QNTY,TURNOVER_LACS,NO_OF_TRADES,DELIV_QTY,DELIV_PER
RELIANCE,EQ,15-Aug-2026,1400,1405,1420,1395,1410,1412,1408,1000000,14080.00,50000,700000,70.00
ASMTEC,EQ,15-Aug-2026,100,101,103,99,102,102,101,50000,50.50,900,6000,12.00
NODELIV,EQ,15-Aug-2026,10,10,10,10,10,10,10,100,0.10,5,-,-
RELIANCE,BE,15-Aug-2026,1400,1405,1420,1395,1410,1412,1408,10,0.14,2,10,100.00
"""


class _Resp:
    def __init__(self, status, text=""):
        self.status = status
        self._text = text

    async def text(self):
        return self._text

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


class _Session:
    """Serves a 404 for every URL except the one naming ``good_day``."""

    def __init__(self, good_day=None, text=CSV, exc=None):
        self.good_day = good_day
        self.text = text
        self.exc = exc
        self.urls = []

    def get(self, url, **kwargs):
        self.urls.append(url)
        if self.exc:
            raise self.exc
        if self.good_day and nd.url_for(self.good_day) == url:
            return _Resp(200, self.text)
        return _Resp(404)


# --- parsing --------------------------------------------------------------


def test_turnover_converts_lacs_to_crore():
    """NSE quotes lacs; the dashboard speaks crore. A missed divisor here
    would overstate every holding's turnover by 100x."""
    rows = nd.parse_delivery_csv(CSV)
    assert rows["RELIANCE"]["turnover_cr"] == 140.80
    assert rows["ASMTEC"]["turnover_cr"] == 0.51


def test_delivery_percentage_is_read():
    rows = nd.parse_delivery_csv(CSV)
    assert rows["RELIANCE"]["deliv_pct"] == 70.0
    assert rows["ASMTEC"]["deliv_pct"] == 12.0


def test_unreported_delivery_stays_none_rather_than_zero():
    """NSE writes "-" where delivery is not reported. "Not reported" and
    "nothing delivered" are different facts and must not collapse."""
    rows = nd.parse_delivery_csv(CSV)
    assert rows["NODELIV"]["deliv_pct"] is None


def test_only_the_eq_series_is_kept():
    """The same symbol trades under BE and BZ with different liquidity;
    merging them would misstate both."""
    rows = nd.parse_delivery_csv(CSV)
    # The BE row for RELIANCE must not have overwritten the EQ one.
    assert rows["RELIANCE"]["turnover_cr"] == 140.80


def test_parsing_junk_returns_empty_rather_than_raising():
    assert nd.parse_delivery_csv("") == {}
    assert nd.parse_delivery_csv(None) == {}


# --- classification -------------------------------------------------------


def test_delivery_bands():
    assert nd.classify_delivery(12.0) == "churn"
    assert nd.classify_delivery(40.0) == "mixed"
    assert nd.classify_delivery(70.0) == "delivery-led"
    assert nd.classify_delivery(None) == "unknown"


def test_the_note_fires_only_when_delivery_undercuts_turnover():
    """Saying "70% delivered" about a healthy stock is noise. Saying
    "Rs 8 Cr traded but 12% delivered" changes what the turnover means."""
    assert nd.delivery_note({"deliv_pct": 70.0, "turnover_cr": 140.8}) is None
    assert nd.delivery_note({"deliv_pct": None}) is None

    note = nd.delivery_note({"deliv_pct": 12.0, "turnover_cr": 0.51})
    assert "12% delivered" in note
    assert "intraday churn" in note


# --- fetching -------------------------------------------------------------


def test_url_uses_ddmmyyyy_not_iso():
    assert nd.url_for(datetime.date(2026, 8, 15)).endswith(
        "sec_bhavdata_full_15082026.csv"
    )


def test_walks_back_to_the_last_published_session():
    """Weekends and holidays have no file, and today's is not published until
    after the close. A single attempt would return nothing most mornings."""
    friday = datetime.date(2026, 8, 14)
    session = _Session(good_day=friday)
    rows = asyncio.run(nse_fetch(session, day=datetime.date(2026, 8, 16)))  # a Sunday
    assert rows["RELIANCE"]["deliv_pct"] == 70.0
    assert len(session.urls) == 3  # Sunday, Saturday, then Friday


def nse_fetch(session, day):
    return nd.fetch_delivery_async(session, day=day)


def test_gives_up_after_the_lookback_window():
    session = _Session(good_day=None)
    rows = asyncio.run(nd.fetch_delivery_async(session, day=datetime.date(2026, 8, 16)))
    assert rows == {}
    assert len(session.urls) == nd.MAX_LOOKBACK_DAYS + 1


def test_a_network_failure_is_not_fatal():
    session = _Session(exc=RuntimeError("archive down"))
    assert asyncio.run(nd.fetch_delivery_async(session)) == {}


# --- application ----------------------------------------------------------


def _watchlist():
    return {
        "Energy": [{"ticker": "RELIANCE", "name": "Reliance", "screener": {"pe": 20}}],
        "Tech": [{"ticker": "ASMTEC", "name": "ASM", "screener": {}}],
        "Other": [{"ticker": "UNKNOWN", "name": "Unlisted"}],
    }


def test_delivery_is_stamped_onto_screener():
    watchlist = _watchlist()
    applied = nd.apply_delivery(watchlist, nd.parse_delivery_csv(CSV))
    assert applied == 2

    reliance = watchlist["Energy"][0]["screener"]
    assert reliance["deliv_pct"] == 70.0
    assert reliance["delivery_band"] == "delivery-led"
    assert reliance["turnover_cr_last"] == 140.80
    # Existing screener content survives.
    assert reliance["pe"] == 20

    assert watchlist["Tech"][0]["screener"]["delivery_band"] == "churn"


def test_holdings_absent_from_the_file_are_left_alone():
    watchlist = _watchlist()
    nd.apply_delivery(watchlist, nd.parse_delivery_csv(CSV))
    assert "deliv_pct" not in (watchlist["Other"][0].get("screener") or {})


def test_apply_survives_junk_watchlists():
    assert nd.apply_delivery(None, {}) == 0
    assert nd.apply_delivery({"S": [None, "x"]}, {"X": {}}) == 0


def test_the_model_declares_the_delivery_fields():
    """Anything absent from CompanyFinancials is dropped on coercion, so the
    scorer would read None no matter what apply_delivery attached. This
    pipeline has shipped that exact bug for turnover and the 52-week range."""
    from models.core import CompanyFinancials

    fields = CompanyFinancials.model_fields
    for name in ("deliv_pct", "delivery_band", "turnover_cr_last"):
        assert name in fields, f"{name} would be silently dropped on coercion"


def test_turnover_last_is_named_apart_from_advt():
    """advt_cr is a multi-session average; this is one session. Conflating
    them would make the dashboard's own numbers disagree with each other."""
    from models.core import CompanyFinancials

    assert "advt_cr" in CompanyFinancials.model_fields
    assert "turnover_cr_last" in CompanyFinancials.model_fields


@pytest.mark.parametrize("bad", [{"deliv_pct": "x"}, {}, None])
def test_note_tolerates_bad_input(bad):
    assert nd.delivery_note(bad) is None or isinstance(nd.delivery_note(bad), str)
