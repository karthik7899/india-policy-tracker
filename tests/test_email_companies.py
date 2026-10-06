"""The email's "Your Holdings" cards (emails/mailer._build_companies_html).

Only holdings with something in the last few days get a card; the rest
are one link away on the dashboard, so the section must not grow with the
watchlist.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from emails.mailer import _CAPS_NORMAL, _build_companies_html  # noqa: E402


def _company(ticker, date, **kw):
    return {
        "ticker": ticker,
        "name": f"{ticker} Ltd",
        "sector": "clean_energy",
        "thesis_status": "Intact",
        "activity": [
            {"date": date, "text": f"{ticker} wins order", "kind": "agreement"}
        ],
        "policies": kw.pop("policies", []),
        **kw,
    }


def test_only_recent_holdings_get_cards():
    digest = {
        "as_of": "2026-10-05",
        "companies": [
            _company("FRESH", "2026-10-04"),
            _company("STALE", "2026-09-20"),
        ],
    }
    html = _build_companies_html(digest)
    assert "FRESH wins order" in html
    assert "STALE" not in html


def test_policy_naming_the_company_counts_as_recent():
    named = {
        "date": "2026-10-05",
        "headline": "State grants land to QUIET",
        "names_company": True,
        "direction": "tailwind",
        "status": "enacted",
    }
    digest = {
        "as_of": "2026-10-05",
        "companies": [_company("QUIET", "2026-08-01", policies=[named])],
    }
    html = _build_companies_html(digest)
    assert "State grants land to QUIET" in html
    assert "&#9650;" in html


def test_overflow_points_to_the_dashboard():
    digest = {
        "as_of": "2026-10-05",
        "companies": [_company(f"C{i}", "2026-10-05") for i in range(9)],
    }
    html = _build_companies_html(digest, {**_CAPS_NORMAL, "companies": 3})
    assert "C2 wins order" in html and "C3 wins order" not in html
    assert "+ 6 more on the" in html
    assert "#/companies" in html


def test_nothing_recent_renders_nothing():
    assert _build_companies_html(None) == ""
    assert _build_companies_html({"as_of": "2026-10-05", "companies": []}) == ""
    old = {"as_of": "2026-10-05", "companies": [_company("OLD", "2026-01-01")]}
    assert _build_companies_html(old) == ""
