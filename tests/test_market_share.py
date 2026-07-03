import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from analysis.market_share import compute_peer_market_share  # noqa: E402
from analysis.early_warning import generate_early_warnings  # noqa: E402
from analysis.rotation import detect_emerging_players  # noqa: E402
from providers.screener import parse_peer_table  # noqa: E402


def _stock(ticker, sales_trend=None, **screener_extra):
    screener = dict(screener_extra)
    if sales_trend is not None:
        screener["sales_trend"] = sales_trend
    return {"ticker": ticker, "name": f"{ticker} Ltd", "screener": screener}


# ---------------------------------------------------------------------------
# compute_peer_market_share
# ---------------------------------------------------------------------------


def test_share_and_trend_math():
    # A: 100 -> 100, B: 100 -> 300 over 4 quarters. B triples; A's share
    # falls from 50% to 25%.
    watchlist = {
        "sector": [
            _stock("AAA", [100, 100, 100, 100, 100]),
            _stock("BBB", [100, 150, 200, 250, 300]),
        ]
    }
    rollup = compute_peer_market_share(watchlist)

    rows = {r["ticker"]: r for r in rollup["sector"]}
    assert rows["AAA"]["share_pct"] == 25.0
    assert rows["AAA"]["share_prev_pct"] == 50.0
    assert rows["AAA"]["change_pp"] == -25.0
    assert rows["BBB"]["change_pp"] == 25.0
    assert rows["AAA"]["lookback_quarters"] == 4

    # Annotations written back onto the stock for downstream signals/UI.
    sc = watchlist["sector"][0]["screener"]
    assert sc["peer_share_pct"] == 25.0
    assert sc["peer_share_change_pp"] == -25.0
    assert sc["peer_group_size"] == 2


def test_rollup_sorted_by_share_desc():
    watchlist = {
        "sector": [
            _stock("SMALL", [10, 10]),
            _stock("BIG", [90, 90]),
        ]
    }
    rollup = compute_peer_market_share(watchlist)
    assert [r["ticker"] for r in rollup["sector"]] == ["BIG", "SMALL"]


def test_lookback_adapts_to_thinnest_series():
    watchlist = {
        "sector": [
            _stock("AAA", [100, 100, 100, 100, 100]),
            _stock("BBB", [100, 120]),  # only 2 quarters
        ]
    }
    rollup = compute_peer_market_share(watchlist)
    assert rollup["sector"][0]["lookback_quarters"] == 1


def test_single_member_sector_skipped():
    watchlist = {"sector": [_stock("ONLY", [100, 110, 120])]}
    assert compute_peer_market_share(watchlist) == {}
    assert "peer_share_pct" not in watchlist["sector"][0]["screener"]


def test_macro_indicators_skipped():
    watchlist = {
        "macro_indicators": [
            _stock("ETF1", [100, 100]),
            _stock("ETF2", [100, 100]),
        ]
    }
    assert compute_peer_market_share(watchlist) == {}


def test_invalid_or_nonpositive_series_excluded():
    watchlist = {
        "sector": [
            _stock("GOOD1", [100, 100]),
            _stock("GOOD2", [50, 60]),
            _stock("ZERO", [0, 100]),
            _stock("JUNK", ["n/a", 100]),
            {"ticker": "NOSC", "name": "No Screener"},
        ]
    }
    rollup = compute_peer_market_share(watchlist)
    assert {r["ticker"] for r in rollup["sector"]} == {"GOOD1", "GOOD2"}


# ---------------------------------------------------------------------------
# Early-warning signals: market share shifts
# ---------------------------------------------------------------------------


def _share_warnings(watchlist):
    return [
        w
        for w in generate_early_warnings({}, watchlist)
        if w["category"] == "Market Share"
    ]


def test_share_loss_flagged_as_risk():
    watchlist = {
        "sector": [
            _stock("AAA", [100, 100, 100, 100, 100]),
            _stock("BBB", [100, 150, 200, 250, 300]),
        ]
    }
    compute_peer_market_share(watchlist)
    warnings = _share_warnings(watchlist)

    loss = [w for w in warnings if w["direction"] == "risk"]
    assert len(loss) == 1
    assert loss[0]["ticker"] == "AAA"
    assert loss[0]["severity"] == "High"  # -25pp is far past the -2pp critical bar
    assert "50.0% → 25.0%" in loss[0]["signal"]

    gain = [w for w in warnings if w["direction"] == "opportunity"]
    assert len(gain) == 1 and gain[0]["ticker"] == "BBB"


def test_small_share_drift_not_flagged():
    # 50.0% -> 49.8% over the window: inside the dead zone.
    watchlist = {
        "sector": [
            _stock("AAA", [1000, 996]),
            _stock("BBB", [1000, 1004]),
        ]
    }
    compute_peer_market_share(watchlist)
    assert _share_warnings(watchlist) == []


# ---------------------------------------------------------------------------
# Early-warning signals: growth-laggard fallback
# ---------------------------------------------------------------------------


def _laggard_warnings(watchlist):
    return [
        w
        for w in generate_early_warnings({}, watchlist)
        if w["category"] == "Growth Laggard"
    ]


def test_growth_laggard_fires_without_share_data():
    watchlist = {
        "sector": [
            _stock("FAST1", qoq_sales_growth=25.0),
            _stock("FAST2", qoq_sales_growth=20.0),
            _stock("SLOW", qoq_sales_growth=2.0),
        ]
    }
    warnings = _laggard_warnings(watchlist)
    assert len(warnings) == 1
    assert warnings[0]["ticker"] == "SLOW"
    assert warnings[0]["direction"] == "risk"


def test_growth_laggard_suppressed_when_share_data_exists():
    watchlist = {
        "sector": [
            _stock("FAST1", sales_trend=[100, 130], qoq_sales_growth=25.0),
            _stock("FAST2", sales_trend=[100, 125], qoq_sales_growth=20.0),
            _stock("SLOW", sales_trend=[100, 101], qoq_sales_growth=2.0),
        ]
    }
    compute_peer_market_share(watchlist)
    # The direct share signal covers SLOW; the proxy must stay quiet.
    assert _laggard_warnings(watchlist) == []


def test_growth_laggard_needs_three_peers():
    watchlist = {
        "sector": [
            _stock("FAST", qoq_sales_growth=25.0),
            _stock("SLOW", qoq_sales_growth=1.0),
        ]
    }
    assert _laggard_warnings(watchlist) == []


# ---------------------------------------------------------------------------
# Competitive threats fed by the Screener peer radar (non-headline channel)
# ---------------------------------------------------------------------------


def test_peer_radar_feeds_competitive_threats():
    watchlist = {
        "sector": [_stock("INCUMBENT", qoq_sales_growth=4.0)],
    }
    data = {
        "peer_competitors": {
            "sector": [
                {"name": "Rising Rival", "ticker": "RIVAL", "sales_var_pct": 42.0}
            ]
        }
    }
    warnings = [
        w
        for w in generate_early_warnings(data, watchlist)
        if w["category"] == "Competitive Threat"
    ]
    assert len(warnings) == 1
    assert warnings[0]["ticker"] == "INCUMBENT"
    assert "Rising Rival" in warnings[0]["signal"]


def test_slow_peers_do_not_trigger_threats():
    watchlist = {"sector": [_stock("INCUMBENT", qoq_sales_growth=4.0)]}
    data = {
        "peer_competitors": {
            "sector": [{"name": "Sleepy Rival", "ticker": "ZZZ", "sales_var_pct": 6.0}]
        }
    }
    warnings = [
        w
        for w in generate_early_warnings(data, watchlist)
        if w["category"] == "Competitive Threat"
    ]
    assert warnings == []


# ---------------------------------------------------------------------------
# parse_peer_table (Screener peers-API fragment)
# ---------------------------------------------------------------------------

_PEERS_HTML = """
<table>
  <thead>
    <tr>
      <th>S.No.</th><th>Name</th><th>CMP Rs.</th><th>P/E</th>
      <th>Mar Cap Rs.Cr.</th><th>Div Yld %</th><th>NP Qtr Rs.Cr.</th>
      <th>Qtr Profit Var %</th><th>Sales Qtr Rs.Cr.</th>
      <th>Qtr Sales Var %</th><th>ROCE %</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>1.</td><td><a href="/company/RIVAL/consolidated/">Rising Rival</a></td>
      <td>250.0</td><td>30</td><td>12,500</td><td>0.5</td><td>80</td>
      <td>12</td><td>1,000</td><td>42.5</td><td>18</td>
    </tr>
    <tr>
      <td>2.</td><td><a href="/company/TRACKED/">Already Tracked</a></td>
      <td>100</td><td>20</td><td>5,000</td><td>1</td><td>50</td>
      <td>5</td><td>400</td><td>10</td><td>15</td>
    </tr>
    <tr>
      <td>3.</td><td>Median: 10 companies</td>
      <td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td>
    </tr>
  </tbody>
</table>
"""


def test_parse_peer_table_extracts_all_rows():
    rows = parse_peer_table(_PEERS_HTML)
    assert [r["ticker"] for r in rows] == ["RIVAL", "TRACKED"]
    rival = rows[0]
    assert rival["name"] == "Rising Rival"
    assert rival["sales_var_pct"] == 42.5
    assert rival["market_cap"] == 12500.0
    assert rival["sales_qtr"] == 1000.0
    assert rows[1]["sales_qtr"] == 400.0


def test_parse_peer_table_handles_garbage():
    assert parse_peer_table("") == []
    assert parse_peer_table("<div>no table here</div>") == []
    assert parse_peer_table("<table><tr><td>headerless</td></tr></table>") == []


# ---------------------------------------------------------------------------
# Broadened headline discovery (verb pattern)
# ---------------------------------------------------------------------------

_WATCHLIST = {
    "sector": [{"ticker": "TATAPOWER", "name": "Tata Power"}],
}


def test_verb_pattern_catches_suffixless_names():
    brief = {"sector": [{"title": "Dixon wins Rs 250 crore BEL order"}]}
    emerging = detect_emerging_players(brief, _WATCHLIST)
    assert "Dixon" in emerging.get("sector", [])


def test_suffix_pattern_still_works():
    brief = {"sector": [{"title": "Kaynes Technologies bags new contract"}]}
    emerging = detect_emerging_players(brief, _WATCHLIST)
    assert any("Kaynes" in name for name in emerging.get("sector", []))


def test_government_actors_ignored():
    brief = {
        "sector": [
            {"title": "Centre unveils new PLI scheme"},
            {"title": "Cabinet expands solar incentives"},
            {"title": "SEBI launches new framework"},
        ]
    }
    assert detect_emerging_players(brief, _WATCHLIST) == {}


def test_watchlist_names_not_rediscovered():
    brief = {"sector": [{"title": "Tata Power wins grid contract"}]}
    emerging = detect_emerging_players(brief, _WATCHLIST)
    assert emerging.get("sector", []) == []


def test_honorifics_not_detected_as_companies():
    brief = {
        "sector": [
            {"title": "Shri Amit Shah launches cyber security drive"},
            {"title": "PM Modi unveils semiconductor mission"},
        ]
    }
    assert detect_emerging_players(brief, _WATCHLIST) == {}
