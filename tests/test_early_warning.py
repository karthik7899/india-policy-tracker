import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from analysis.early_warning import generate_early_warnings, _to_float  # noqa: E402


def _categories(warnings):
    return {w["category"] for w in warnings}


def test_empty_inputs_return_empty_list():
    assert generate_early_warnings({}, {}) == []
    assert generate_early_warnings({}, None) == []


def test_macro_indicators_sector_is_skipped():
    watchlist = {
        "macro_indicators": [
            {
                "ticker": "MAKEINDIA",
                "name": "Make in India ETF",
                "screener": {"qoq_sales_growth": -10.0},
            }
        ]
    }
    assert generate_early_warnings({}, watchlist) == []


def test_risk_rules_trigger_expected_categories():
    watchlist = {
        "clean_energy": [
            {
                "ticker": "RISKY",
                "name": "Risky Corp",
                "percent_change": -9.0,
                "screener": {
                    "promoter_change": -2.5,
                    "fii_change": -3.5,
                    "qoq_sales_growth": -8.0,
                    "current_ratio": 0.8,
                    "debt_to_equity": 1.4,
                    "opm_expansion": -3.0,
                    "valuation_alerts": ["High P/E", "High P/E"],
                },
            }
        ]
    }
    warnings = generate_early_warnings({}, watchlist)
    cats = _categories(warnings)
    assert {
        "Promoter Exit",
        "FII Outflow",
        "Revenue Contraction",
        "Liquidity Stress",
        "High Leverage",
        "Margin Compression",
        "Valuation Stretch",
        "Price Breakdown",
    } <= cats
    # Promoter exit and a -9% session both qualify as Critical severity.
    assert any(w["severity"] == "Critical" for w in warnings)
    # Valuation alerts are de-duplicated into a single consolidated signal.
    val = [w for w in warnings if w["category"] == "Valuation Stretch"][0]
    assert val["signal"].count("High P/E") == 1
    assert all(w["direction"] == "risk" for w in warnings)


def test_opportunity_rules_trigger_expected_categories():
    data = {
        "corporate_agreements": [
            {"company": "Winner Corp", "title": "Mega defence MoU"}
        ]
    }
    watchlist = {
        "aerospace_defence": [
            {
                "ticker": "WIN",
                "name": "Winner Corp",
                "percent_change": 6.0,
                "volume_surge": 3.0,
                "screener": {"fii_change": 1.2, "dii_change": 0.9},
            }
        ]
    }
    warnings = generate_early_warnings(data, watchlist)
    cats = _categories(warnings)
    assert {
        "Institutional Accumulation",
        "Policy Catalyst",
        "Momentum Breakout",
    } <= cats
    assert all(w["direction"] == "opportunity" for w in warnings)


def test_risks_sorted_before_opportunities_then_by_severity():
    watchlist = {
        "clean_energy": [
            {
                "ticker": "MIX",
                "name": "Mixed Corp",
                "screener": {
                    "fii_change": 1.0,  # opportunity (Medium)
                    "dii_change": 1.0,  # opportunity (paired -> High)
                    "current_ratio": 0.5,  # risk (High)
                },
            }
        ]
    }
    warnings = generate_early_warnings({}, watchlist)
    directions = [w["direction"] for w in warnings]
    # All risks come before any opportunity.
    assert directions == sorted(directions, key=lambda d: 0 if d == "risk" else 1)
    assert directions[0] == "risk"


def test_missing_and_string_fields_do_not_raise():
    watchlist = {
        "fmcg": [
            {"ticker": "A", "name": "Alpha", "screener": None},
            {"ticker": "B", "name": "Beta"},  # no screener key at all
            {
                "ticker": "C",
                "name": "Gamma",
                "percent_change": "-6.5%",
                "screener": {"debt_to_equity": "1.20", "fii_change": "N/A"},
            },
            "not-a-dict",
        ]
    }
    warnings = generate_early_warnings({}, watchlist)
    # String "-6.5%" parses to a Price Breakdown; "1.20" parses to High Leverage.
    cats = _categories(warnings)
    assert "Price Breakdown" in cats
    assert "High Leverage" in cats


def test_to_float_handles_varied_inputs():
    assert _to_float(None) is None
    assert _to_float(True) is None
    assert _to_float("—") is None
    assert _to_float("N/A") is None
    assert _to_float("+15.5%") == 15.5
    assert _to_float("1,250") == 1250.0
    assert _to_float(3) == 3.0


def test_competitive_threat_flags_lagging_incumbent():
    # A high-growth challenger discovered in the sector out-grows a slow incumbent.
    watchlist = {
        "fmcg": [
            {
                "ticker": "SLOW",
                "name": "Slowpoke Foods",
                "screener": {"qoq_sales_growth": 6.0},
            },
            {
                "ticker": "FAST",
                "name": "Fast Foods",
                "screener": {"qoq_sales_growth": 25.0},
            },
        ]
    }
    data = {
        "emerging_players": {
            "fmcg": [
                {
                    "name": "Challenger Corp",
                    "ticker": "CHAL",
                    "status": "Pipeline",
                    "qoq_growth": 40.0,
                }
            ]
        }
    }
    warnings = generate_early_warnings(data, watchlist)
    threats = [w for w in warnings if w["category"] == "Competitive Threat"]
    # Only the lagging incumbent (below the 15% bar) is flagged, not the fast grower.
    assert len(threats) == 1
    assert threats[0]["ticker"] == "SLOW"
    assert threats[0]["direction"] == "risk"
    assert "Challenger Corp" in threats[0]["signal"]


def test_competitive_threat_ignored_when_challenger_growth_unknown():
    watchlist = {
        "fmcg": [
            {"ticker": "SLOW", "name": "Slow", "screener": {"qoq_sales_growth": 5.0}}
        ]
    }
    # Challenger has no qoq_growth -> cannot establish a credible threat.
    data = {
        "emerging_players": {
            "fmcg": [{"name": "Mystery Co", "ticker": "MYST", "status": "Pipeline"}]
        }
    }
    warnings = generate_early_warnings(data, watchlist)
    assert "Competitive Threat" not in _categories(warnings)


# ---------------------------------------------------------------------------
# every alert can explain itself
# ---------------------------------------------------------------------------


def test_every_emitted_category_has_a_documented_rule():
    """The guard against the failure this feature exists to prevent.

    A first draft of the rule book guessed category names instead of reading
    them, leaving the largest group ("Market Share", ten of twenty-two alerts
    that day) explained as "Rule not documented" while looking complete.
    """
    from analysis.early_warning import _RULE_BOOK
    import re
    import pathlib

    source = pathlib.Path(__file__).parent.parent / "analysis"
    emitted = set()
    for path in source.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        # Categories reach the alert dict either through emit(...) or a
        # literal "category" key.
        emitted.update(re.findall(r'"category":\s*"([^"]+)"', text))
        for match in re.finditer(r'emit\(\s*"[^"]+",\s*"[^"]+",\s*"([^"]+)"', text):
            emitted.add(match.group(1))

    undocumented = {c for c in emitted if c not in _RULE_BOOK}
    assert not undocumented, f"categories with no rule documented: {undocumented}"


def test_annotation_labels_headline_derived_findings_as_low_confidence():
    """Headline-derived alerts inherit every NLP classification error, and
    must not present with the same authority as a reported figure."""
    from analysis.early_warning import annotate_rule

    numeric = annotate_rule({"category": "Margin Compression"})
    headline = annotate_rule({"category": "Competitive Threat"})

    assert numeric["confidence"] == "High"
    assert headline["confidence"] == "Low"
    assert "Screener" in numeric["evidence_source"]
    assert "Headline" in headline["evidence_source"]


def test_an_unknown_category_is_labelled_honestly_not_confidently():
    from analysis.early_warning import annotate_rule

    alert = annotate_rule({"category": "Something New"})
    assert alert["rule"] == "Rule not documented"
    assert alert["confidence"] == "Medium"


class TestOrderMateriality:
    """Sizing an alert against the revenue of the company it belongs to.

    The whole feature turns on measuring each headline separately. The first
    version read the joined signal prose, which on real data meant a joint
    venture figure and a Rs 20,000 crore sector procurement number arrived as
    one string with the company's own news, and the guards could not tell
    which sentence they were rejecting.
    """

    # Rs 2,000 crore TTM, so Rs 500 crore is 25% and Rs 40 crore is 2%.
    WATCHLIST = {
        "defence": [
            {
                "ticker": "MIDCAP",
                "name": "Midcap Ltd",
                "screener": {"sales_trend": [480.0, 500.0, 510.0, 510.0]},
            }
        ]
    }

    def _alert(self, titles, severity="Medium", direction="opportunity"):
        return {
            "ticker": "MIDCAP",
            "category": "Policy Catalyst",
            "severity": severity,
            "direction": direction,
            "signal": "Active policy tailwind — " + "; ".join(titles),
            "source_headlines": [
                {"kind": "Agreement", "title": t, "label": f"Agreement: {t}"}
                for t in titles
            ],
        }

    def test_a_material_order_escalates_one_step(self):
        from analysis.early_warning import annotate_order_materiality

        alert = self._alert(["Midcap wins order worth Rs 500 crore"])
        annotate_order_materiality([alert], self.WATCHLIST)

        assert alert["severity"] == "High"
        assert alert["materiality_pct"] == 25.0
        assert "of trailing revenue" in alert["signal"]

    def test_an_immaterial_order_is_sized_but_not_escalated(self):
        """Below the bar the number is still worth showing; the severity is
        not the place to show it."""
        from analysis.early_warning import annotate_order_materiality

        alert = self._alert(["Midcap wins order worth Rs 40 crore"])
        annotate_order_materiality([alert], self.WATCHLIST)

        assert alert["severity"] == "Medium"
        assert alert["materiality_pct"] == 2.0
        assert alert["materiality_band"] == "minor"

    def test_escalation_is_one_way(self):
        """A large order alongside a Critical finding must never soften it."""
        from analysis.early_warning import annotate_order_materiality

        alert = self._alert(
            ["Midcap wins order worth Rs 500 crore"], severity="Critical"
        )
        annotate_order_materiality([alert], self.WATCHLIST)
        assert alert["severity"] == "Critical"

    def test_risk_alerts_are_never_escalated_on_order_size(self):
        """Direction is a property of the finding, not of its size."""
        from analysis.early_warning import annotate_order_materiality

        alert = self._alert(["Midcap wins order worth Rs 500 crore"], direction="risk")
        annotate_order_materiality([alert], self.WATCHLIST)

        assert alert["severity"] == "Medium"
        assert alert["materiality_pct"] == 25.0  # sized, just not escalated

    def test_each_headline_is_measured_on_its_own(self):
        """The real regression. A sector procurement figure sharing an alert
        with the company's own order must not be read as the company's."""
        from analysis.early_warning import annotate_order_materiality

        alert = self._alert(
            [
                "Midcap wins order worth Rs 40 crore",
                "Zen jumps 9%, Midcap hits upper circuit as India eyes "
                "Rs 20,000 crore drone buy",
            ]
        )
        annotate_order_materiality([alert], self.WATCHLIST)

        assert alert["materiality_pct"] == 2.0
        assert alert["severity"] == "Medium"

    def test_a_joint_venture_figure_does_not_escalate(self):
        from analysis.early_warning import annotate_order_materiality

        alert = self._alert(
            ["Midcap, Kaga Electronics Form Rs 250 crore EMS Joint Venture"]
        )
        annotate_order_materiality([alert], self.WATCHLIST)

        assert alert["severity"] == "Medium"
        assert "materiality_pct" not in alert

    def test_the_basis_headline_is_recorded(self):
        """A severity the reader cannot trace back to a headline is a claim
        without a source."""
        from analysis.early_warning import annotate_order_materiality

        alert = self._alert(
            ["Midcap signs supply agreement", "Midcap wins order worth Rs 500 crore"]
        )
        annotate_order_materiality([alert], self.WATCHLIST)
        assert alert["materiality_basis"] == "Midcap wins order worth Rs 500 crore"

    def test_prose_alerts_without_headlines_are_left_alone(self):
        """Rule alerts state a computed condition; any number in one is a
        percentage point, not an order value."""
        from analysis.early_warning import annotate_order_materiality

        alert = {
            "ticker": "MIDCAP",
            "category": "Market Share",
            "severity": "Medium",
            "direction": "opportunity",
            "signal": "Gaining revenue share: 12.0% → 500.0% over 4 periods.",
        }
        annotate_order_materiality([alert], self.WATCHLIST)

        assert alert["severity"] == "Medium"
        assert "materiality_pct" not in alert

    def test_an_unknown_ticker_is_sized_against_nothing(self):
        from analysis.early_warning import annotate_order_materiality

        alert = self._alert(["Midcap wins order worth Rs 500 crore"])
        alert["ticker"] = "NOTHELD"
        annotate_order_materiality([alert], self.WATCHLIST)

        assert alert["severity"] == "Medium"
        assert "materiality_pct" not in alert

    def test_malformed_input_never_raises(self):
        from analysis.early_warning import annotate_order_materiality

        assert annotate_order_materiality(None, None) is None
        assert annotate_order_materiality([None, {}, 7], {}) is not None
