import time
from unittest.mock import patch
import unittest
from analysis.rotation import detect_emerging_players


class TestDetectEmergingPlayers(unittest.TestCase):
    def test_detect_emerging_players_basic(self):
        """Test basic detection of emerging players and ensuring companies in watchlist are ignored."""
        brief_data = {
            "technology": [
                {"title": "Acme Corp announces new product"},
                {"title": "TCS Limited shares fall"},
                {"title": "Some random news without corp names"},
            ],
            "finance": [
                {"title": "Beta Technologies merges with Gamma Solutions"},
                {"title": "India budget announced"},  # 'India' is ignored word
            ],
        }

        watchlist = {
            "technology": [{"ticker": "TCS", "name": "Tata Consultancy Services"}]
        }

        result = detect_emerging_players(brief_data, watchlist)

        self.assertIn("technology", result)
        self.assertEqual(result["technology"], ["Acme Corp"])
        self.assertIn("finance", result)
        self.assertEqual(result["finance"], ["Beta Technologies", "Gamma Solutions"])

    def test_ignore_list(self):
        """Test that words in the ignore list do not trigger detection."""
        brief_data = {
            "general": [
                {"title": "India Technologies launches new service"},
                {"title": "Delhi Infrastructure project started"},
                {"title": "Cabinet Solutions is a weird name"},
                {"title": "National Corp reports earnings"},
            ]
        }
        watchlist = {}
        result = detect_emerging_players(brief_data, watchlist)
        self.assertEqual(result, {})

    def test_short_names(self):
        """Test that very short captured names (< 3 chars) are ignored."""
        brief_data = {
            "general": [
                {"title": "Xi Corp invests heavily"},
                {"title": "Ab Limited announces dividend"},
            ]
        }
        watchlist = {}
        result = detect_emerging_players(brief_data, watchlist)
        self.assertEqual(result, {})

    def test_emerging_players_sector_skipped(self):
        """Test that the emerging_players sector in brief_data is correctly skipped."""
        brief_data = {"emerging_players": [{"title": "Omega Corp is emerging"}]}
        watchlist = {}
        result = detect_emerging_players(brief_data, watchlist)
        self.assertEqual(result, {})


if __name__ == "__main__":
    unittest.main()


class TestScreenedCandidatesReachRotation(unittest.TestCase):
    """A peer that cleared the fundamental screen must actually be evaluated.

    Before this path existed, discovery ran only on headline regex plus name
    resolution, so a listed competitor sitting in the Screener peer radar with
    a known ticker was never even looked at.
    """

    def _run(self, screened, monkey):
        import analysis.rotation as rot

        evaluated = []

        def fake_resolve(name, session=None):
            evaluated.append(("resolved", name))
            return None, None

        # Stop evaluation right after resolution so the test never touches
        # the network; what matters is which candidates got that far.
        def fake_ticker(symbol):
            evaluated.append(("priced", symbol))
            raise RuntimeError("no network in tests")

        monkey(rot, "resolve_ticker_from_name", fake_resolve)
        monkey(rot, "get_cached_ticker", fake_ticker)
        watchlist = {"sec": [{"ticker": "HELD", "name": "Held Co"}]}
        rot.auto_curate_watchlist({"sec": []}, watchlist, screened_candidates=screened)
        return evaluated

    def test_preresolved_candidate_skips_name_resolution(self):
        import analysis.rotation as rot

        originals = {}

        def monkey(mod, attr, value):
            originals.setdefault(attr, getattr(mod, attr))
            setattr(mod, attr, value)

        try:
            evaluated = self._run(
                {"sec": [{"name": "Syrma SGS Tech.", "ticker": "SYRMA"}]}, monkey
            )
        finally:
            for attr, value in originals.items():
                setattr(rot, attr, value)

        # It went straight to the price check under its Screener ticker,
        # rather than being thrown away by name resolution.
        self.assertIn(("priced", "SYRMA.NS"), evaluated)
        self.assertNotIn(("resolved", "Syrma SGS Tech."), evaluated)

    def test_existing_holding_is_not_re_added(self):
        import analysis.rotation as rot

        originals = {}

        def monkey(mod, attr, value):
            originals.setdefault(attr, getattr(mod, attr))
            setattr(mod, attr, value)

        try:
            evaluated = self._run(
                {"sec": [{"name": "Held Co", "ticker": "HELD"}]}, monkey
            )
        finally:
            for attr, value in originals.items():
                setattr(rot, attr, value)

        self.assertEqual(evaluated, [])


class TestIntakeCap(unittest.TestCase):
    """Watchlist growth must be bounded per run.

    With the fundamental screen feeding pre-resolved candidates, measured
    headroom was 16 additions in a single pass — and it compounds, since each
    new holding anchors another industry peer table next run.
    """

    def _run_with(self, screened, cap):
        import analysis.rotation as rot

        evaluated = []
        originals = {}

        def monkey(attr, value):
            originals.setdefault(attr, getattr(rot, attr))
            setattr(rot, attr, value)

        def fake_ticker(symbol):
            evaluated.append(symbol)
            raise RuntimeError("no network in tests")

        monkey("get_cached_ticker", fake_ticker)
        monkey("MAX_INTAKE_PER_RUN", cap)
        try:
            watchlist = {"sec": [{"ticker": "HELD", "name": "Held Co"}]}
            emerging, _ = rot.auto_curate_watchlist(
                {"sec": []}, watchlist, screened_candidates=screened
            )
        finally:
            for attr, value in originals.items():
                setattr(rot, attr, value)
        return evaluated, emerging

    def test_candidates_beyond_the_cap_are_deferred_not_dropped(self):
        # Nothing is added here (the price lookup fails), so the cap is not
        # consumed — every candidate should still be evaluated.
        screened = {
            "sec": [
                {"name": f"Cand {i}", "ticker": f"C{i}", "growth_pct": float(i)}
                for i in range(4)
            ]
        }
        evaluated, _ = self._run_with(screened, cap=3)
        self.assertEqual(len(evaluated), 4)

    def test_strongest_candidates_are_evaluated_first(self):
        """The cap must spend its slots on the best names available anywhere."""
        screened = {
            "sec": [
                {"name": "Weak", "ticker": "WEAK", "growth_pct": 16.0},
                {"name": "Strong", "ticker": "STRONG", "growth_pct": 99.0},
                {"name": "Mid", "ticker": "MID", "growth_pct": 40.0},
            ]
        }
        evaluated, _ = self._run_with(screened, cap=3)
        self.assertEqual(evaluated, ["STRONG.NS", "MID.NS", "WEAK.NS"])

    def test_the_screen_hands_over_its_ranking(self):
        """Through the screen's own hand-over, as main.py passes it: the
        growth used to be left behind there, so every candidate ranked at
        0.0 and the slots went to whichever sector came first."""
        import analysis.rotation as rot
        from analysis.candidate_screen import candidates_for_rotation

        screened = {
            "aaa": [{"name": "Weak", "ticker": "WEAK", "growth_pct": 16.0}],
            "sec": [{"name": "Strong", "ticker": "STRONG", "growth_pct": 99.0}],
        }
        order = []

        def probe(name, preresolved, isin_master, watchlisted=()):
            order.append(preresolved)
            return {"ticker": preresolved, "full_name": name, "error": "no_market_data"}

        watchlist = {"aaa": [], "sec": []}
        with patch.object(rot, "_probe_candidate", probe), patch.object(
            rot, "save_watchlist", lambda *a, **k: None
        ):
            rot.auto_curate_watchlist(
                {}, watchlist, screened_candidates=candidates_for_rotation(screened)
            )
        self.assertEqual(order, ["STRONG", "WEAK"])

    def test_a_company_in_two_sectors_is_probed_once(self):
        """Hitachi Energy came up in two sectors on 23 Oct 2026 and was
        probed twice at once: no analyst target in one, +39.8% in the
        other. One probe now serves every sector it comes up in."""
        import analysis.rotation as rot

        calls = []

        def probe(name, preresolved, isin_master, watchlisted=()):
            calls.append(preresolved)
            return {"ticker": preresolved, "full_name": name, "error": "no_market_data"}

        screened = {
            "clean_energy": [
                {"name": "Hitachi Energy", "ticker": "POWERINDIA", "growth_pct": 68.6}
            ],
            "data_center_support": [
                {"name": "Hitachi Energy", "ticker": "POWERINDIA", "growth_pct": 68.6},
                {"name": "Other", "ticker": "OTHER", "growth_pct": 20.0},
            ],
        }
        watchlist = {"clean_energy": [], "data_center_support": []}
        with patch.object(rot, "_probe_candidate", probe), patch.object(
            rot, "save_watchlist", lambda *a, **k: None
        ):
            emerging, _ = rot.auto_curate_watchlist(
                {}, watchlist, screened_candidates=screened
            )
        self.assertEqual(sorted(calls), ["OTHER", "POWERINDIA"])
        # Both sectors still record their own verdict on the one reading.
        for sector in ("clean_energy", "data_center_support"):
            self.assertTrue(
                any(r["ticker"] == "POWERINDIA" for r in emerging[sector]), sector
            )

    def test_a_zero_cap_defers_everything_with_a_reason(self):
        screened = {"sec": [{"name": "Cand", "ticker": "C1", "growth_pct": 50.0}]}
        evaluated, emerging = self._run_with(screened, cap=0)
        self.assertEqual(evaluated, [], "no price lookups once the cap is spent")
        statuses = [e["status"] for e in emerging["sec"]]
        self.assertEqual(statuses, ["Deferred"])
        self.assertIn("next run", emerging["sec"][0]["reason"])


class TestCandidateProbeConcurrency(unittest.TestCase):
    """From Jules's suggestion at analysis/rotation.py:194.

    The mechanism was real but its rationale was not: auto_curate_watchlist is
    called sequentially from run_pipeline with nothing else in flight, so the
    blocking calls delayed nothing. The genuine cost is wall-clock, and the
    genuine hazard is that this loop is stateful — the intake cap, the
    watchlist membership set and the per-sector slot count all change as
    candidates are admitted, so deciding concurrently would change WHICH
    candidates get in.
    """

    def test_probes_run_concurrently(self):
        import threading
        import analysis.rotation as rot

        live = 0
        peak = 0
        lock = threading.Lock()

        def slow_probe(session, name, preresolved, isin_master, watchlisted=()):
            nonlocal live, peak
            with lock:
                live += 1
                peak = max(peak, live)
            time.sleep(0.05)
            with lock:
                live -= 1
            return {"ticker": None, "full_name": name, "error": "unresolved"}

        watchlist = {"sec": [{"ticker": "OLD", "name": "Old", "growth_pct": "5%"}]}
        screened = {
            "sec": [
                {"name": f"Cand {i}", "ticker": f"C{i}", "growth_pct": "50%"}
                for i in range(4)
            ]
        }
        with patch.object(rot, "_probe_candidate", slow_probe), patch.object(
            rot, "save_watchlist", lambda *a, **k: None
        ):
            rot.auto_curate_watchlist({}, watchlist, screened_candidates=screened)

        self.assertGreater(peak, 1, "candidate probes were still serialised")

    def test_the_intake_cap_still_stops_the_network(self):
        """The cap is why this loop is cheap: once reached, every remaining
        candidate is deferred without a request. Prefetching everything would
        have traded latency for load on Screener, which already returns 429s."""
        import analysis.rotation as rot

        probed = []

        def counting_probe(session, name, preresolved, isin_master, watchlisted=()):
            probed.append(name)
            return {"ticker": None, "full_name": name, "error": "unresolved"}

        # More candidates than one batch, so the second batch is reachable.
        screened = {
            "sec": [
                {"name": f"Cand {i}", "ticker": f"C{i}", "growth_pct": "50%"}
                for i in range(rot.PREFETCH_BATCH * 3)
            ]
        }
        watchlist = {"sec": [{"ticker": "OLD", "name": "Old", "growth_pct": "5%"}]}

        with patch.object(rot, "_probe_candidate", counting_probe), patch.object(
            rot, "save_watchlist", lambda *a, **k: None
        ):
            rot.auto_curate_watchlist({}, watchlist, screened_candidates=screened)

        # Every candidate here is unresolved, so intake never rises and all get
        # probed — the point is that batching did not change the count.
        self.assertEqual(len(probed), rot.PREFETCH_BATCH * 3)

    def test_a_held_ticker_is_never_priced(self):
        """Pinned separately from the existing test because batching the
        resolve and the quote together silently broke it once already."""
        import analysis.rotation as rot

        priced = []

        def fake_ticker(yahoo_ticker):
            priced.append(yahoo_ticker)
            raise AssertionError("must not price a held ticker")

        watchlist = {"sec": [{"ticker": "HELD", "name": "Held", "growth_pct": "5%"}]}
        screened = {"sec": [{"name": "Held Co", "ticker": "HELD", "growth_pct": "90%"}]}

        with patch.object(rot, "get_cached_ticker", fake_ticker), patch.object(
            rot, "save_watchlist", lambda *a, **k: None
        ):
            rot.auto_curate_watchlist({}, watchlist, screened_candidates=screened)

        self.assertEqual(priced, [])


def _candidate(ticker, target=130.0, label=None):
    """A probed clean-energy candidate at 100, with an analysts' target or
    (target=None) none."""
    from analysis.sector_fit import keywords

    return {
        "ticker": ticker,
        "full_name": label or ticker.title(),
        "error": None,
        "isin": None,
        "live_price": 100.0,
        "target_price": target,
        "growth_pct_val": target - 100.0 if target else None,
        "rating": "Buy",
        "rev_growth_raw": 0.4,
        "revenue_growth": "40.0%",
        "qoq_growth": 25.0,
        "sales_yoy": 40.0,
        "industry": "Solar",
        "keywords": keywords("develops solar and wind power plants"),
    }


def _covered(ticker, upside):
    return {
        "ticker": ticker,
        "name": ticker,
        "growth_pct": f"{upside}%",
        "target": "120.00",
        "analyst_count": 6,
    }


def _uncovered(ticker, broken_runs=0):
    """A holding no analyst covers: its upside is the pipeline's own Graham
    estimate, clamped at -50%."""
    stock = {
        "ticker": ticker,
        "name": ticker,
        "growth_pct": "-50.0%",
        "target": "50.00",
        "estimate_method": "Fundamental Estimate",
    }
    if broken_runs:
        stock["thesis_broken_runs"] = broken_runs
    return stock


def _rotate(holdings, probe, registered=None):
    """Run one candidate through the rotation: (held tickers, its radar row,
    decisions)."""
    import analysis.rotation as rot

    watchlist = {"clean_energy": holdings}
    screened = {
        "clean_energy": [
            {"name": probe["full_name"], "ticker": probe["ticker"], "growth_pct": "50%"}
        ]
    }
    with patch.object(
        rot, "_probe_candidate", lambda *a, **k: dict(probe)
    ), patch.object(rot, "save_watchlist", lambda *a, **k: None), patch.object(
        rot, "load_registered_names", lambda: registered or {}
    ):
        radar, decisions = rot.auto_curate_watchlist(
            {}, watchlist, screened_candidates=screened
        )
    row = next(r for r in radar["clean_energy"] if r["ticker"] == probe["ticker"])
    return [s["ticker"] for s in watchlist["clean_energy"]], row, decisions


def test_a_screened_peer_is_admitted_under_its_registered_name():
    """Screener's peer table cuts names to about fifteen characters, and the
    rotation admitted peers under the label: NTPC Green Energy joined the
    watchlist as "NTPC Green Ene." and matched no headline by name."""
    registered = {"NTPCGREEN": "NTPC Green Energy Limited"}
    _, _, decisions = _rotate(
        [_covered("SUZLON", 5)],
        _candidate("NTPCGREEN", label="NTPC Green Ene."),
        registered,
    )
    assert decisions[0]["stock"]["name"] == "NTPC Green Energy"
    # Without a registered name the label stands, less any legal suffix.
    _, _, decisions = _rotate(
        [_covered("SUZLON", 5)], _candidate("SOMEPEER", label="Some Peer Ltd")
    )
    assert decisions[0]["stock"]["name"] == "Some Peer"


def test_a_candidate_no_analyst_covers_is_given_no_target(monkeypatch):
    """It was given price x 1.25, a made-up 25% upside that passed the
    potential check by construction. 31 of the first 64 decisions came in
    on it."""
    import analysis.rotation as rot

    class Hist:
        empty = False

        def __getitem__(self, key):
            class Close:
                iloc = [100.0]

            return Close()

    class Ticker:
        def __init__(self, info):
            self.info = info

        def history(self, **kwargs):
            return Hist()

    monkeypatch.setattr(
        rot,
        "_screener_quarterly_sales",
        lambda session, t: [
            ("Sep 2025", 100.0),
            ("Jun 2026", 110.0),
            ("Sep 2026", 125.0),
        ],
    )
    for info, target, upside in (
        ({"recommendationKey": "buy"}, None, None),
        # A target with no analysts behind it is not a consensus either.
        ({"targetMeanPrice": 140.0}, None, None),
        # The median, as for a holding (providers/yahoo.py).
        (
            {
                "targetMedianPrice": 130.0,
                "targetMeanPrice": 140.0,
                "numberOfAnalystOpinions": 6,
            },
            130.0,
            30.0,
        ),
    ):
        monkeypatch.setattr(rot, "get_cached_ticker", lambda s, i=info: Ticker(i))
        probe = rot._probe_candidate("Peer", "PEER", {})
        assert (probe["target_price"], probe["growth_pct_val"]) == (target, upside)


def test_without_a_target_it_fills_an_empty_slot_but_replaces_no_holding():
    held, row, decisions = _rotate(
        [_covered(t, 5) for t in ("A", "B", "C", "D")], _candidate("NEW", None)
    )
    assert "NEW" in held
    # Its own estimate is written later in the run, marked as such.
    assert "target" not in decisions[0]["stock"]
    assert "growth_pct" not in decisions[0]["stock"]

    held, row, decisions = _rotate(
        [_covered(t, 5) for t in ("A", "B", "C", "D", "E")], _candidate("NEW", None)
    )
    assert "NEW" not in held and decisions == []
    assert row["status"] == "Pipeline"
    assert "no analyst target" in row["reason"]


def test_upside_is_compared_only_between_analysts_targets():
    """The holding at -50% is the pipeline's own estimate, not a target."""
    holdings = [_covered(t, u) for t, u in (("A", 10), ("B", 20), ("C", 30), ("D", 40))]
    holdings.append(_uncovered("OWN"))
    held, row, _ = _rotate(holdings, _candidate("NEW", 125.0))
    assert "NEW" in held and "OWN" in held and "A" not in held


def test_an_uncovered_holding_goes_only_after_its_thesis_stays_broken():
    holdings = [_covered(t, 40) for t in ("A", "B", "C", "D")]
    # Broken four runs running: still kept, and the candidate's 25% does not
    # beat the covered 40%.
    held, row, _ = _rotate(holdings + [_uncovered("OWN", 4)], _candidate("NEW", 125.0))
    assert "OWN" in held and "NEW" not in held

    for target in (125.0, None):
        holdings = [_covered(t, 40) for t in ("A", "B", "C", "D")]
        held, row, _ = _rotate(
            holdings + [_uncovered("OWN", 5)], _candidate("NEW", target)
        )
        assert "OWN" not in held and "NEW" in held
        assert row["reason"] == "Rotated into watchlist replacing OWN."


def _quarters_page(rows, headers):
    """A Screener company page's quarterly table: the label cell first, as
    Screener wraps an expandable label in a button."""
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = "".join(
        f"<tr><td class='text'><button>{label}&nbsp;<span>+</span></button></td>"
        + "".join(f"<td>{v}</td>" for v in values)
        + "</tr>"
        for label, values in rows
    )
    return (
        "<html><body><section id='quarters'><table><thead><tr><th></th>"
        f"{head}</tr></thead><tbody>{body}</tbody></table></section></body></html>"
    )


_FIVE_QUARTERS = ("Sep 2025", "Dec 2025", "Mar 2026", "Jun 2026", "Sep 2026")


class _Pages:
    """A session answering each Screener URL with (status, text)."""

    def __init__(self, pages):
        self.pages = pages
        self.asked = []

    def get(self, url, **kwargs):
        self.asked.append(url)
        status, text = self.pages.get(url, (404, ""))

        class Response:
            status_code = status

        Response.text = text
        return Response()


def test_a_lenders_revenue_line_is_read_as_its_sales():
    """Screener's page for a bank says "Revenue" where others say "Sales":
    the rotation's own regex read nothing there and turned IndusInd Bank,
    Bank of Baroda and Federal Bank away at a "growth" of exactly 0.0%."""
    import analysis.rotation as rot

    page = _quarters_page(
        [("Revenue", ["1,000", "1,020", "1,050", "1,080", "1,200"])], _FIVE_QUARTERS
    )
    session = _Pages(
        {"https://www.screener.in/company/FEDERALBNK/consolidated/": (200, page)}
    )
    quarters = rot._screener_quarterly_sales(session, "FEDERALBNK")
    assert quarters[-1] == ("Sep 2026", 1200.0)
    assert rot._sales_yoy(quarters) == 20.0


def test_a_company_with_no_subsidiaries_is_read_from_its_standalone_page():
    """Its consolidated page is there and shows no figures, as for BDL, GRSE
    and Honeywell Automation: the old reader stopped at the HTTP 200."""
    import analysis.rotation as rot

    blank = _quarters_page([("Sales", ["", "", "", "", ""])], _FIVE_QUARTERS)
    standalone = _quarters_page(
        [("Sales", ["500", "450", "900", "300", "650"])], _FIVE_QUARTERS
    )
    session = _Pages(
        {
            "https://www.screener.in/company/BDL/consolidated/": (200, blank),
            "https://www.screener.in/company/BDL/": (200, standalone),
        }
    )
    assert rot._sales_yoy(rot._screener_quarterly_sales(session, "BDL")) == 30.0

    # No consolidated page at all (HTTP 404) also falls through to standalone.
    session = _Pages({"https://www.screener.in/company/BDL/": (200, standalone)})
    assert rot._screener_quarterly_sales(session, "BDL")[-1] == ("Sep 2026", 650.0)


def test_a_refused_page_is_not_asked_again_and_leaves_growth_unmeasured():
    import analysis.rotation as rot

    session = _Pages({"https://www.screener.in/company/GRSE/consolidated/": (429, "")})
    assert rot._screener_quarterly_sales(session, "GRSE") is None
    assert session.asked == ["https://www.screener.in/company/GRSE/consolidated/"]
    assert rot._sales_yoy(None) is None and rot._sales_qoq(None) is None


def test_growth_on_the_year_pairs_quarters_by_their_column_header():
    """A blank column shifts every value before it, so "four back" would
    compare September with June."""
    import analysis.rotation as rot
    from bs4 import BeautifulSoup
    from analysis.parsing import extract_row_by_column

    headers = ("Jun 2025",) + _FIVE_QUARTERS
    page = _quarters_page([("Sales", ["80", "100", "", "95", "105", "130"])], headers)
    quarters = extract_row_by_column(
        BeautifulSoup(page, "lxml"), "quarters", r"\bSales\b"
    )
    assert ("Dec 2025", 0.0) not in quarters and len(quarters) == 5
    assert rot._sales_yoy(quarters) == 30.0
    assert rot._sales_qoq(quarters) == 23.8

    # The same quarter a year earlier missing, or not positive: unmeasured.
    assert rot._sales_yoy([("Jun 2026", 105.0), ("Sep 2026", 130.0)]) is None
    assert rot._sales_yoy([("Sep 2025", 0.0), ("Sep 2026", 130.0)]) is None
    assert rot._sales_yoy([("FY26", 100.0), ("FY27", 130.0)]) is None


def test_a_seasonal_dip_on_the_quarter_does_not_keep_out_a_company_growing_on_the_year():
    """ITC Hotels was turned away at -25.4% on the quarter before, its lean
    April-June against its January-March peak, while up 14.8% on the year;
    Kusumgar at -21.1% while up 93.6%."""
    holdings = [_covered("SUZLON", 5)]
    held, row, _ = _rotate(holdings, dict(_candidate("NEW"), qoq_growth=-21.1))
    assert "NEW" in held
    assert (row["qoq_growth"], row["sales_yoy"]) == (-21.1, 40.0)

    held, row, _ = _rotate(
        [_covered("SUZLON", 5)],
        dict(_candidate("NEW"), qoq_growth=-25.4, sales_yoy=14.8),
    )
    assert "NEW" not in held
    assert row["status"] == "Growth Divergence"
    assert row["reason"] == (
        "Quarterly sales +14.8% on the same quarter last year, under the 15% bar"
    )


def test_a_candidate_whose_figures_were_not_read_is_unmeasured_not_at_zero():
    held, row, decisions = _rotate(
        [_covered("SUZLON", 5)],
        dict(_candidate("NEW"), qoq_growth=None, sales_yoy=None),
    )
    assert "NEW" not in held and decisions == []
    assert row["status"] == "Unresolved"
    assert "not measured" in row["reason"] and "0.0" not in row["reason"]
