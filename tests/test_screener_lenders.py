"""A lender's Screener page (providers/screener.py).

Screener lays out banks and NBFCs on a template of their own: the top line is
"Revenue" and where every other page has "OPM %" it has "Financing Margin %".
The parser looked for "Sales" and "OPM" only, so HDFCBANK, ICICIBANK and SBIN
never had quarterly sales or a margin. The rows here are the ones Screener
served for HDFCBANK, SBIN and ICICIBANK on 14 Oct 2026
(docs/upstream-findings.md).
"""

import datetime

from analysis import ask
from analysis import event_calendar as ec
from analysis.early_warning import generate_early_warnings
from analysis.graham import _earning_power_is_intact
from models.core import CompanyFinancials
from providers.screener import parse_company_page


def _section(section_id, rows):
    body = "".join(
        f"<tr><td>{label}</td>" + "".join(f"<td>{v}</td>" for v in values) + "</tr>"
        for label, values in rows
    )
    return f'<section id="{section_id}"><table><tbody>{body}</tbody></table></section>'


def _lender(margins):
    return [
        ("Revenue <button>+</button>", ["80,000", "84,000", "87,000"]),
        ("Interest", ["47,000", "49,000", "50,500"]),
        ("Expenses <button>+</button>", ["21,000", "22,500", "24,000"]),
        ("Financing Profit", ["12,000", "12,500", "12,500"]),
        ("Financing Margin %", margins),
        ("Net Profit <button>+</button>", ["16,500", "17,000", "17,600"]),
        ("EPS in Rs", ["21.6", "22.2", "23.0"]),
        ("Gross NPA %", ["1.33%", "1.40%", "1.24%"]),
    ]


MAKER_ROWS = [
    ("Sales <button>+</button>", ["1,000", "1,100"]),
    ("Expenses <button>+</button>", ["850", "920"]),
    ("Operating Profit", ["150", "180"]),
    ("OPM %", ["15%", "16%"]),
]


def _parse(rows, ticker="HDFCBANK"):
    page = _section("quarters", rows) + _section("profit-loss", rows)
    sc, _w = parse_company_page(f"<html><body>{page}</body></html>", ticker, "x")
    return sc


def test_a_lenders_revenue_is_read_as_its_sales():
    sc = _parse(_lender(["15%", "15%", "14%"]))
    assert sc["q_sales"] == 87000.0 and sc["sales_trend"][-1] == 87000.0
    assert sc["qoq_sales_growth"] == 3.57
    assert sc["annual_sales_trend"] == [80000.0, 84000.0, 87000.0]


def test_a_lenders_financing_margin_is_kept_apart_from_an_operating_margin():
    sc = _parse(_lender(["15%", "15%", "14%"]))
    assert sc["q_fin_margin"] == 14.0 and sc["fin_margin_trend"] == [15.0, 15.0, 14.0]
    for key in ("q_opm", "opm_expansion", "quarterly_ebitda_margin"):
        assert key not in sc
    # Capex is not estimated as 5% of interest earned.
    assert sc["capex"] == 0.0


def test_icici_banks_negative_financing_margin_is_not_an_operating_loss():
    """ICICIBANK's consolidated financing margin was -12% on 14 Oct 2026: the
    insurance arm's income is not in it. Read as an operating margin it would
    zero the bank's Graham value and raise a margin warning."""
    sc = _parse(_lender(["-2%", "-8%", "-12%"]), "ICICIBANK")
    assert _earning_power_is_intact(CompanyFinancials(**sc))
    stock = {"ticker": "ICICIBANK", "name": "ICICI Bank", "screener": sc}
    categories = {
        w["category"]
        for w in generate_early_warnings({}, {"banking_financials": [stock]})
    }
    assert "Margin Compression" not in categories


def test_a_manufacturers_page_reads_as_before():
    sc = _parse(MAKER_ROWS, "HAL")
    assert sc["q_sales"] == 1100.0 and sc["q_opm"] == 16.0
    assert "q_fin_margin" not in sc
    assert sc["capex"] == 220.0


def test_ask_is_told_a_lenders_revenue_and_financing_margin():
    sc = _parse(_lender(["15%", "15%", "14%"]))
    latest = ask._figures({}, sc)["latest_quarter"]
    assert latest["revenue_cr"] == 87000.0 and latest["financing_margin_pct"] == 14.0
    assert "sales_cr" not in latest and "operating_margin_pct" not in latest


def test_a_lenders_results_card_says_revenue_and_financing_margin():
    held = {
        "name": "State Bank of India",
        "sector": "banking_financials",
        "stock": {"ticker": "SBIN", "screener": _parse(_lender(["15%", "15%", "14%"]))},
    }
    card = ec.scorecard("SBIN", held, datetime.date(2026, 10, 30))
    assert card["margin_basis"] == "financing" and card["opm_change_pp"] == -1.0
    assert card["summary"].startswith("Revenue ₹87,000 Cr")
    assert "financing margin 14%" in card["summary"]
