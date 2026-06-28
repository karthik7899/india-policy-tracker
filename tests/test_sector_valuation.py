import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from analysis.sector_valuation import (  # noqa: E402
    build_sector_valuation,
    _relative_label,
    _to_float,
)


def _stock(ticker, pe, **extra):
    sc = {"pe_ratio": pe}
    sc.update(extra)
    return {"ticker": ticker, "name": ticker, "price": "100", "screener": sc}


def test_build_sector_valuation_median_and_annotation():
    watchlist = {
        "clean_energy": [
            _stock("A", 10.0),
            _stock("B", 20.0),
            _stock("C", 30.0),
        ]
    }
    rollup = build_sector_valuation(watchlist)
    assert len(rollup) == 1
    entry = rollup[0]
    assert entry["median_pe"] == 20.0
    assert entry["stock_count"] == 3
    assert entry["cheapest_ticker"] == "A"
    assert entry["most_expensive_ticker"] == "C"

    # Each priced stock is annotated with the peer median and a relative label.
    sc_a = watchlist["clean_energy"][0]["screener"]
    assert sc_a["industry_pe"] == 20.0
    assert "below peers" in sc_a["pe_vs_peers"]


def test_macro_indicators_and_invalid_pe_are_skipped():
    watchlist = {
        "macro_indicators": [_stock("ETF", 15.0)],
        "fmcg": [
            _stock("X", "N/A"),
            _stock("Y", 0),
            _stock("Z", 25.0),
        ],
    }
    rollup = build_sector_valuation(watchlist)
    sectors = {r["sector"] for r in rollup}
    assert "macro_indicators" not in sectors
    # Only Z has a usable P/E in fmcg.
    fmcg = next(r for r in rollup if r["sector"] == "fmcg")
    assert fmcg["stock_count"] == 1
    assert fmcg["median_pe"] == 25.0


def test_rollup_sorted_cheapest_first():
    watchlist = {
        "clean_energy": [_stock("A", 40.0)],
        "fmcg": [_stock("X", 12.0)],
    }
    rollup = build_sector_valuation(watchlist)
    assert [r["median_pe"] for r in rollup] == [12.0, 40.0]


def test_relative_label_bands():
    assert _relative_label(8.0, 10.0) == "20% below peers"
    assert _relative_label(13.0, 10.0) == "30% above peers"
    assert _relative_label(10.5, 10.0) == "In line with peers"
    assert _relative_label(10.0, 0) == "—"


def test_empty_and_missing_screener_safe():
    assert build_sector_valuation({}) == []
    assert build_sector_valuation({"fmcg": [{"ticker": "X", "name": "X"}]}) == []


def test_to_float_coercion():
    assert _to_float("12.5") == 12.5
    assert _to_float(None) is None
    assert _to_float("N/A") is None
    assert _to_float(True) is None
