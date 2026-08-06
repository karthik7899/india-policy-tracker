"""Tests for per-holding news coverage (analysis/coverage.py).

The point of this module is the audit trail, so most of these assert on what
gets *rejected* and why. A coverage list that silently drops items is the same
failure the badge exists to expose: "no news" and "news the matcher refused"
look identical from outside.
"""

import datetime
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from analysis import coverage as cov  # noqa: E402

_TODAY = datetime.date.today()


def _iso(days_ago):
    return (_TODAY - datetime.timedelta(days=days_ago)).isoformat()


def _watchlist():
    return {
        "clean_energy": [{"ticker": "SUZLON", "name": "Suzlon Energy"}],
        "macro_indicators": [{"ticker": "NIFTY", "name": "Nifty"}],
    }


def _news(title, days_ago=1, link="https://example.com/a", source="Example"):
    return {"title": title, "date": _iso(days_ago), "link": link, "source": source}


class TestAttribution:
    def test_counts_only_headlines_that_name_the_holding(self):
        data = {
            "clean_energy": [
                _news("Suzlon wins 300 MW order"),
                _news("Some other company wins an order"),
            ]
        }
        result = cov.build_coverage(data, _watchlist())
        assert cov.counts_for(result["SUZLON"]) == 1

    def test_macro_indicators_are_not_holdings(self):
        result = cov.build_coverage(
            {"macro_indicators": [_news("Nifty rises")]}, _watchlist()
        )
        assert "NIFTY" not in result


class TestAuditTrail:
    def test_a_duplicate_phrasing_is_recorded_as_merged_not_dropped(self):
        """Counting the same launch twice was a real scoring defect; the audit
        is how a reader can see the merge happened at all."""
        data = {
            "clean_energy": [
                _news("Suzlon wins 300 MW order"),
                _news("Suzlon wins 300 MW order!"),
            ]
        }
        items = cov.build_coverage(data, _watchlist())["SUZLON"]
        assert cov.counts_for(items) == 1
        merged = [i for i in items if i["status"] == "merged"]
        assert len(merged) == 1
        assert "merged" in merged[0]["exclusion_reason"]

    def test_an_out_of_window_item_is_excluded_with_its_age(self):
        data = {"clean_energy": [_news("Suzlon wins order", days_ago=200)]}
        items = cov.build_coverage(data, _watchlist())["SUZLON"]
        assert cov.counts_for(items) == 0
        assert items[0]["status"] == "excluded"
        assert "aged" in items[0]["exclusion_reason"]
        assert "200" in items[0]["exclusion_reason"]

    def test_an_item_inside_the_window_counts(self):
        data = {
            "clean_energy": [_news("Suzlon wins order", days_ago=cov.WINDOW_DAYS - 1)]
        }
        items = cov.build_coverage(data, _watchlist())["SUZLON"]
        assert cov.counts_for(items) == 1

    def test_an_undated_item_is_not_treated_as_stale(self):
        """No date is not the same statement as old."""
        data = {"clean_energy": [{"title": "Suzlon wins order", "link": "u"}]}
        items = cov.build_coverage(data, _watchlist())["SUZLON"]
        assert cov.counts_for(items) == 1


class TestItemShape:
    def test_every_item_carries_the_fields_the_drawer_renders(self):
        data = {"clean_energy": [_news("Suzlon wins 300 MW order")]}
        item = cov.build_coverage(data, _watchlist())["SUZLON"][0]
        for field in (
            "date",
            "headline",
            "source_url",
            "source_label",
            "event_tags",
            "confidence",
            "status",
        ):
            assert field in item, field

    def test_event_engine_items_are_high_confidence(self):
        """Their actors were already resolved to tickers, so attribution is
        not a guess the way a headline match is."""
        data = {
            "market_events": [
                {
                    "headline": "Suzlon secures order",
                    "actors": ["SUZLON"],
                    "date": _iso(1),
                    "event_type": "order_win",
                }
            ]
        }
        item = cov.build_coverage(data, _watchlist())["SUZLON"][0]
        assert item["confidence"] == "H"
        assert "order_win" in item["event_tags"]


class TestCounts:
    def test_counts_exclude_merged_and_excluded_items(self):
        """The badge must agree with the score, which counts neither."""
        data = {
            "clean_energy": [
                _news("Suzlon wins 300 MW order"),
                _news("Suzlon wins 300 MW order."),
                _news("Suzlon commissions plant", days_ago=400),
            ]
        }
        result = cov.build_coverage(data, _watchlist())
        assert cov.coverage_counts(result) == {"SUZLON": 1}
        assert len(result["SUZLON"]) == 3  # all three still auditable

    def test_a_malformed_corpus_yields_no_coverage_rather_than_an_error(self):
        assert cov.build_coverage(None, None) == {}
        assert cov.build_coverage({"clean_energy": ["junk"]}, _watchlist()) == {}


class TestSidecars:
    def test_sidecars_are_written_per_ticker_and_stale_ones_removed(self, tmp_path):
        from history import store

        original = store.NEWS_DIR
        store.NEWS_DIR = str(tmp_path / "news")
        try:
            store.write_coverage_sidecars(
                {"SUZLON": [{"headline": "a", "status": "counted"}]}
            )
            path = tmp_path / "news" / "SUZLON.json"
            assert path.exists()
            assert json.loads(path.read_text())["items"][0]["headline"] == "a"

            # A holding rotated out must stop serving its last coverage.
            store.write_coverage_sidecars(
                {"TCS": [{"headline": "b", "status": "counted"}]}
            )
            assert not path.exists()
            assert (tmp_path / "news" / "TCS.json").exists()
        finally:
            store.NEWS_DIR = original

    def test_a_hostile_ticker_cannot_escape_the_news_directory(self, tmp_path):
        from history import store

        original = store.NEWS_DIR
        store.NEWS_DIR = str(tmp_path / "news")
        try:
            store.write_coverage_sidecars({"../../etc/passwd": [{"headline": "x"}]})
            assert not (tmp_path / "etc").exists()
            written = list((tmp_path / "news").glob("*.json"))
            assert all(".." not in p.name for p in written)
        finally:
            store.NEWS_DIR = original


class TestBadgeAgreesWithSidecar:
    """The badge number and the drawer contents must be the same claim.

    They are produced by different code paths — a payload dict and a per-ticker
    file — and nothing but this test stops them drifting apart.
    """

    def test_counts_match_sidecar_contents_for_every_ticker(self, tmp_path):
        from history import store

        data = {
            "clean_energy": [
                _news("Suzlon wins 300 MW order"),
                _news("Suzlon wins 300 MW order."),  # merged
                _news("Suzlon commissions plant", days_ago=400),  # excluded
                _news("Suzlon signs supply agreement"),
            ]
        }
        coverage = cov.build_coverage(data, _watchlist())
        counts = cov.coverage_counts(coverage)

        original = store.NEWS_DIR
        store.NEWS_DIR = str(tmp_path / "news")
        try:
            store.write_coverage_sidecars(coverage)
            for ticker, expected in counts.items():
                written = json.loads(
                    (tmp_path / "news" / f"{ticker}.json").read_text()
                )["items"]
                counted = [i for i in written if i["status"] == "counted"]
                assert len(counted) == expected, ticker
                # And the audit rows survive the round trip.
                assert len(written) > len(counted)
        finally:
            store.NEWS_DIR = original

    def test_the_payload_never_invents_a_coverage_key(self):
        """A run that computed no coverage must not claim it looked."""
        from dashboard.payload import build_display_payload

        assert "coverage_count" not in build_display_payload({"early_warnings": []})
        assert build_display_payload({"coverage_count": {"X": 2}})[
            "coverage_count"
        ] == {"X": 2}
        assert build_display_payload({"coverage_count": "junk"})["coverage_count"] == {}
