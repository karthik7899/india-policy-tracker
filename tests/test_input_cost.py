"""Tests for price-based input-cost shocks (analysis/input_cost.py).

The direction convention carries the whole feature. A rising USDINR is a
weaker rupee: pressure on an EMS importer, relief for an IT exporter. A map
that scored both as "FX exposure" would flag the wrong half of the watchlist
on every currency move, so most of these tests are about signs.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from analysis.input_cost import (  # noqa: E402
    classify,
    compute_input_cost_shock,
    input_cost_warnings,
)
from config_commodities import COMMODITY_MAP  # noqa: E402

_QUIET = {key: {"first": 100.0, "last": 100.5, "sessions": 22} for key in COMMODITY_MAP}


def _prices(**moves):
    """Every input flat except the ones named, moved by a percentage."""
    out = dict(_QUIET)
    for key, pct in moves.items():
        out[key] = {"first": 100.0, "last": 100.0 * (1 + pct / 100), "sessions": 22}
    return out


class TestBands:
    def test_thresholds(self):
        assert classify(20.0) == "severe"
        assert classify(7.0) == "material"
        assert classify(1.0) == "quiet"
        assert classify(None) == "unmeasured"

    def test_bands_are_symmetric(self):
        """A 20% fall is as much of an event as a 20% rise."""
        assert classify(-20.0) == "severe"
        assert classify(-7.0) == "material"


class TestDirection:
    def test_a_weaker_rupee_pressures_importers_and_helps_exporters(self):
        shock = compute_input_cost_shock(_prices(usdinr=10.0))
        sectors = shock["sectors"]
        assert sectors["manufacturing_electronics"]["score"] > 0
        assert sectors["semiconductors_equipment"]["score"] > 0
        assert sectors["midcap_it"]["score"] < 0
        assert sectors["midcap_it"]["direction"] == "tailwind"

    def test_a_stronger_rupee_reverses_both(self):
        shock = compute_input_cost_shock(_prices(usdinr=-10.0))
        sectors = shock["sectors"]
        assert sectors["manufacturing_electronics"]["score"] < 0
        assert sectors["midcap_it"]["score"] > 0

    def test_crude_pressures_consumers_and_lifts_refiners(self):
        shock = compute_input_cost_shock(_prices(crude=15.0))
        sectors = shock["sectors"]
        assert sectors["logistics_heavy_capital"]["score"] > 0
        assert sectors["big_cap_industries"]["score"] < 0

    def test_opposing_inputs_net_off_rather_than_double_count(self):
        """Textiles consume crude and export in dollars, so a simultaneous
        crude spike and rupee fall partly cancel."""
        both = compute_input_cost_shock(_prices(crude=10.0, usdinr=10.0))
        crude_only = compute_input_cost_shock(_prices(crude=10.0))
        assert (
            both["sectors"]["textiles_apparel"]["score"]
            < crude_only["sectors"]["textiles_apparel"]["score"]
        )


class TestWeighting:
    def test_the_same_move_hits_exposed_sectors_harder(self):
        """Copper is 30% of clean energy's mapped cost base and 20% of
        industrial manufacturing's."""
        shock = compute_input_cost_shock(_prices(copper=20.0))
        assert (
            shock["sectors"]["clean_energy"]["score"]
            > shock["sectors"]["industrial_manufacturing"]["score"]
        )

    def test_the_weighted_score_stays_in_percentage_points(self):
        """18% copper against a 0.30 weight is a 5.4% effective move."""
        shock = compute_input_cost_shock(_prices(copper=18.0))
        assert shock["sectors"]["clean_energy"]["score"] == 5.4

    def test_drivers_are_ranked_by_contribution(self):
        shock = compute_input_cost_shock(_prices(copper=20.0, crude=6.0))
        drivers = shock["sectors"]["industrial_manufacturing"]["drivers"]
        assert drivers[0]["input"] == "copper"


class TestQuietAndMissing:
    def test_a_quiet_input_raises_no_sector(self):
        assert compute_input_cost_shock(_QUIET)["sectors"] == {}

    def test_a_quiet_input_is_still_reported_as_measured(self):
        """Silence and "we looked and it was calm" are different claims."""
        shock = compute_input_cost_shock(_QUIET)
        assert len(shock["inputs"]) == len(COMMODITY_MAP)
        assert shock["inputs"]["copper"]["band"] == "quiet"
        assert shock["unmeasured"] == []

    def test_a_failed_fetch_is_unmeasured_not_unchanged(self):
        """The failure this guards: a blocked price source reading as a calm
        market. yfinance returns an empty frame rather than raising."""
        prices = dict(_QUIET)
        prices["copper"] = {"error": "price fetch returned no data this run"}
        shock = compute_input_cost_shock(prices)

        assert "copper" not in shock["inputs"]
        assert any(u["input"] == "copper" for u in shock["unmeasured"])
        assert "clean_energy" not in shock["sectors"]

    def test_a_zero_base_does_not_divide(self):
        prices = dict(_QUIET)
        prices["copper"] = {"first": 0.0, "last": 5.0, "sessions": 22}
        shock = compute_input_cost_shock(prices)
        assert any(u["input"] == "copper" for u in shock["unmeasured"])

    def test_every_input_failing_yields_no_sectors_and_no_exception(self):
        prices = {k: {"error": "unreachable"} for k in COMMODITY_MAP}
        shock = compute_input_cost_shock(prices)
        assert shock["sectors"] == {}
        assert len(shock["unmeasured"]) == len(COMMODITY_MAP)

    def test_malformed_input_never_raises(self):
        assert compute_input_cost_shock({})["sectors"] == {}
        assert isinstance(compute_input_cost_shock({"copper": None}), dict)


class TestWarnings:
    def test_a_severe_move_raises_a_high_alert(self):
        shock = compute_input_cost_shock(_prices(copper=45.0))
        alerts = input_cost_warnings(shock)
        clean = [a for a in alerts if a["sector"] == "clean_energy"]
        assert clean and clean[0]["severity"] == "High"
        assert clean[0]["direction"] == "risk"

    def test_a_tailwind_is_an_opportunity_not_a_risk(self):
        shock = compute_input_cost_shock(_prices(usdinr=30.0))
        it = [a for a in input_cost_warnings(shock) if a["sector"] == "midcap_it"]
        assert it and it[0]["direction"] == "opportunity"

    def test_quiet_sectors_raise_nothing(self):
        assert input_cost_warnings(compute_input_cost_shock(_QUIET)) == []

    def test_the_signal_names_the_input_and_the_move(self):
        shock = compute_input_cost_shock(_prices(copper=20.0))
        alert = input_cost_warnings(shock)[0]
        assert "Copper" in alert["signal"]
        assert "+20.0%" in alert["signal"]

    def test_language_stays_in_the_review_register(self):
        shock = compute_input_cost_shock(_prices(copper=45.0, usdinr=30.0))
        for alert in input_cost_warnings(shock):
            lowered = alert["signal"].lower()
            assert "buy" not in lowered and "sell" not in lowered

    def test_malformed_shock_never_raises(self):
        assert input_cost_warnings(None) == []
        assert input_cost_warnings({"sectors": {"x": None}}) == []


class TestConfigIntegrity:
    def test_every_exposure_names_a_real_sector(self):
        from config import SECTOR_METADATA

        for key, cfg in COMMODITY_MAP.items():
            for sector, _weight, _side in cfg["exposure"]:
                assert sector in SECTOR_METADATA, f"{key} -> unknown sector {sector}"

    def test_every_exposure_declares_a_side(self):
        """A defaulted side is the bug the map exists to prevent."""
        for key, cfg in COMMODITY_MAP.items():
            for sector, _weight, side in cfg["exposure"]:
                assert side in ("consumer", "producer"), f"{key} -> {sector}"

    def test_weights_are_plausible_shares(self):
        for key, cfg in COMMODITY_MAP.items():
            for sector, weight, _side in cfg["exposure"]:
                assert 0 < weight <= 1.0, f"{key} -> {sector} weight {weight}"
