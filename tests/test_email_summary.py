"""Tests for the daily email summary (emails/summary.py) and the variants it
selects in emails/mailer.py.

The subject line these replace was the date. The failure mode being guarded
against is subtler than an ugly subject: a subject that states counts the body
contradicts, or a short email on a broken run that reads like a quiet one.
"""

import datetime
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from emails import summary as summary_mod  # noqa: E402
from emails.mailer import build_briefing_email  # noqa: E402

_TODAY = datetime.date(2026, 8, 5)


def _warning(ticker, severity="Medium", direction="risk", status="new", **kw):
    base = {
        "ticker": ticker,
        "name": f"{ticker} Ltd",
        "sector": kw.pop("sector", "clean_energy"),
        "severity": severity,
        "direction": direction,
        "status": status,
        "category": kw.pop("category", "Margin Compression"),
        "signal": kw.pop("signal", "OPM fell 12pp"),
    }
    base.update(kw)
    return base


def _watchlist(n=10, priced=None, with_screener=None):
    priced = n if priced is None else priced
    with_screener = n if with_screener is None else with_screener
    stocks = []
    for i in range(n):
        s = {"ticker": f"T{i}", "name": f"T{i} Ltd"}
        if i < priced:
            s["price"] = "100.00"
        if i < with_screener:
            s["screener"] = {"pe_ratio": 20.0, "revenue_ttm_growth_pct": 5.0}
        stocks.append(s)
    return {"clean_energy": stocks}


def _brief(warnings=None, **kw):
    data = {
        "early_warnings": warnings or [],
        "warning_summary": [],
        "thesis_health": {},
    }
    data.update(kw)
    return data


class TestDayType:
    def test_a_busy_day_is_normal(self):
        s = summary_mod.build_summary(
            _brief([_warning("BPCL", "Critical")]), _watchlist()
        )
        assert s["day_type"] == "normal"

    def test_no_new_or_escalated_signals_is_quiet(self):
        s = summary_mod.build_summary(
            _brief([_warning("BPCL", status="ongoing")]), _watchlist()
        )
        assert s["day_type"] == "quiet"

    def test_thin_coverage_is_degraded_even_with_signals(self):
        """A broken run must not be reported as a busy one."""
        s = summary_mod.build_summary(
            _brief([_warning("BPCL", "Critical")]),
            _watchlist(10, priced=2, with_screener=2),
        )
        assert s["day_type"] == "degraded"

    def test_degraded_outranks_quiet(self):
        """Both produce a short email; they mean opposite things."""
        s = summary_mod.build_summary(
            _brief([_warning("X", status="ongoing")]),
            _watchlist(10, priced=1, with_screener=1),
        )
        assert s["day_type"] == "degraded"


class TestSubject:
    def test_the_subject_names_counts_not_just_a_date(self):
        s = summary_mod.build_summary(
            _brief(
                [
                    _warning("BPCL", "Critical"),
                    _warning("DIXON", direction="opportunity"),
                ]
            ),
            _watchlist(),
        )
        subject = summary_mod.build_subject(s, _TODAY)
        assert "1 Critical" in subject
        assert "1 Opportunities" in subject
        assert "05 Aug" in subject

    def test_a_quiet_subject_says_so_and_carries_the_standing_count(self):
        s = summary_mod.build_summary(
            _brief(
                [_warning("X", status="ongoing")],
                warning_summary=[{"count": 18}],
            ),
            _watchlist(),
        )
        subject = summary_mod.build_subject(s, _TODAY)
        assert "No new signals" in subject
        assert "18 ongoing" in subject

    def test_a_degraded_subject_leads_with_the_warning(self):
        """The reader must know before opening that the data is thin."""
        s = summary_mod.build_summary(
            _brief([_warning("BPCL", "Critical")]),
            _watchlist(10, priced=2, with_screener=2),
        )
        subject = summary_mod.build_subject(s, _TODAY)
        assert "DEGRADED" in subject
        assert "provisional" in subject
        # It must not advertise signals it has just called unreliable.
        assert "Critical" not in subject

    def test_the_subject_count_matches_the_summary(self):
        """A subject promising more than the body lists is worse than a dull
        one: the reader stops trusting the number."""
        warnings = [_warning(f"T{i}", "Critical") for i in range(3)]
        s = summary_mod.build_summary(_brief(warnings), _watchlist())
        assert "3 Critical" in summary_mod.build_subject(s, _TODAY)
        assert s["critical_total"] == 3


class TestPreheader:
    def test_preheader_names_actual_tickers(self):
        s = summary_mod.build_summary(
            _brief([_warning("BPCL", "Critical", category="Margin Compression")]),
            _watchlist(),
        )
        assert "BPCL" in summary_mod.build_preheader(s)

    def test_degraded_preheader_states_coverage(self):
        s = summary_mod.build_summary(
            _brief([]), _watchlist(10, priced=2, with_screener=2)
        )
        assert "provisional" in summary_mod.build_preheader(s).lower()


class TestPlainText:
    def test_plain_text_exists_and_carries_the_critical_items(self):
        """There was no text/plain part at all before this."""
        s = summary_mod.build_summary(
            _brief([_warning("BPCL", "Critical")]), _watchlist()
        )
        text = summary_mod.build_plain_text(s, "https://example.com", _TODAY)
        assert "BPCL" in text
        assert "https://example.com" in text
        assert "Not investment advice" in text
        assert "<" not in text  # genuinely plain, not stripped markup

    def test_degraded_plain_text_recommends_treating_signals_as_provisional(self):
        s = summary_mod.build_summary(
            _brief([]), _watchlist(10, priced=1, with_screener=1)
        )
        text = summary_mod.build_plain_text(s, "https://example.com", _TODAY)
        assert "DEGRADED RUN" in text
        assert "provisional" in text


class TestVariantSelection:
    def test_a_quiet_day_produces_a_short_email(self):
        """It used to render every sector card in full to say nothing had
        happened, which is how a daily email teaches its reader to skip it."""
        message = build_briefing_email(
            _brief([_warning("X", status="ongoing")], warning_summary=[{"count": 12}]),
            _watchlist(),
        )
        assert len(message["html"].encode("utf-8")) < 10_000
        assert "No new or escalated signals" in message["html"]

    def test_a_degraded_run_produces_a_short_email_that_says_why(self):
        message = build_briefing_email(
            _brief([_warning("BPCL", "Critical")]),
            _watchlist(10, priced=1, with_screener=1),
        )
        assert len(message["html"].encode("utf-8")) < 10_000
        assert "Degraded run" in message["html"]
        assert "provisional" in message["html"]

    def test_a_normal_day_still_gets_the_full_briefing(self):
        message = build_briefing_email(
            _brief([_warning("BPCL", "Critical")]), _watchlist()
        )
        assert "What changed today" in message["html"]

    def test_every_message_carries_all_three_parts(self):
        message = build_briefing_email(
            _brief([_warning("BPCL", "Critical")]), _watchlist()
        )
        assert message["subject"] and message["html"] and message["text"]


class TestCountsAreDeltasNotTotals:
    """The subject must describe what changed, not what is true.

    main.py passes the *untrimmed* corpus to the mailer, so counting every
    warning produced a first production subject reading "11 Critical, 140
    Opportunities" against a dashboard showing 42 actionable items — the wall
    of alerts this rewrite replaced, reproduced in the line most likely to be
    read.
    """

    def _mixed(self):
        return _brief(
            [
                _warning("NEW1", "Critical", status="new"),
                _warning("ESC1", "Critical", status="escalated"),
                _warning("OLD1", "Critical", status="ongoing"),
                _warning("OLD2", "Critical", status="ongoing"),
                _warning("NEWOPP", direction="opportunity", status="new"),
                _warning("OLDOPP1", direction="opportunity", status="ongoing"),
                _warning("OLDOPP2", direction="opportunity", status="ongoing"),
            ]
        )

    def test_critical_counts_only_new_and_escalated(self):
        s = summary_mod.build_summary(self._mixed(), _watchlist())
        assert s["critical_total"] == 2  # not 4

    def test_opportunity_counts_only_new_and_escalated(self):
        s = summary_mod.build_summary(self._mixed(), _watchlist())
        assert s["opportunities_total"] == 1  # not 3

    def test_the_subject_reflects_the_delta(self):
        s = summary_mod.build_summary(self._mixed(), _watchlist())
        subject = summary_mod.build_subject(s, _TODAY)
        assert "2 Critical" in subject
        assert "4 Critical" not in subject

    def test_standing_conditions_are_still_counted_separately(self):
        """Dropping them from the headline must not lose them entirely."""
        s = summary_mod.build_summary(
            _brief(
                [_warning("OLD", status="ongoing")],
                warning_summary=[{"count": 297}],
            ),
            _watchlist(),
        )
        assert s["ongoing_total"] == 297


class TestSectorSelection:
    """Sector cards were ~60% of the email at every tier — 51 KB of an 85 KB
    minimal render — because the ladder trimmed rows inside each card and never
    trimmed the number of cards. Eighteen sectors shipped on a day two moved.
    """

    def _brief_with_sectors(self):
        from config import SECTOR_METADATA

        keys = [k for k in SECTOR_METADATA if k != "macro_indicators"][:5]
        data = _brief(
            [
                # Warnings carry the sector LABEL, not the slug.
                _warning("A", "Critical", sector=SECTOR_METADATA[keys[0]]["label"]),
                _warning("B", "Critical", sector=SECTOR_METADATA[keys[0]]["label"]),
                _warning("C", "Low", sector=SECTOR_METADATA[keys[1]]["label"]),
                _warning(
                    "D",
                    "Ongoing",
                    sector=SECTOR_METADATA[keys[2]]["label"],
                    status="ongoing",
                ),
            ]
        )
        for k in keys:
            # Shape matches what the scrapers emit; the renderer reads
            # impact/source directly.
            data[k] = [
                {
                    "title": f"news for {k}",
                    "link": "u",
                    "date": "",
                    "impact": "Positive",
                    "source": "Test",
                }
            ]
        return data, keys

    def test_the_delta_ranking_matches_on_label_not_only_slug(self):
        """A naive equality check matched nothing, so the ranking silently
        degraded to alphabetical — six sectors chosen by first letter and
        presented as the six that moved most."""
        from emails.mailer import _sector_delta

        data, keys = self._brief_with_sectors()
        assert _sector_delta(keys[0], data) == 8  # two Criticals
        assert _sector_delta(keys[1], data) == 1  # one Low

    def test_ongoing_warnings_do_not_count_as_change(self):
        from emails.mailer import _sector_delta

        data, keys = self._brief_with_sectors()
        assert _sector_delta(keys[2], data) == 0

    def test_sectors_are_ordered_by_delta_and_capped_per_tier(self):
        from emails.mailer import _sectors_to_render, _CAP_LADDER

        data, keys = self._brief_with_sectors()
        for _, caps in _CAP_LADDER:
            selected, eligible = _sectors_to_render(data, caps)
            assert len(selected) <= caps["sectors"]
            assert selected[0] == keys[0]  # highest delta always first
            assert eligible >= len(selected)

    def test_ordering_is_deterministic_across_calls(self):
        """Two sectors tying on delta and news volume must not swap between
        runs — a reordered email reads as new information."""
        from emails.mailer import _sectors_to_render, _CAPS_NORMAL

        data, _ = self._brief_with_sectors()
        first = _sectors_to_render(data, _CAPS_NORMAL)[0]
        for _ in range(5):
            assert _sectors_to_render(data, _CAPS_NORMAL)[0] == first

    def test_a_sector_with_no_change_and_no_news_is_omitted(self):
        from emails.mailer import _sectors_to_render, _CAPS_NORMAL
        from config import SECTOR_METADATA

        quiet_key = [k for k in SECTOR_METADATA if k != "macro_indicators"][-1]
        data = _brief([])
        data[quiet_key] = []
        selected, _ = _sectors_to_render(data, _CAPS_NORMAL)
        assert quiet_key not in selected

    def test_dropped_sectors_are_stated_not_silently_absent(self):
        """ "18 monitored, 6 shown" is a different message from "6 exist"."""
        from emails.mailer import _render_email, _CAPS_NORMAL

        data, keys = self._brief_with_sectors()
        # The sector card renders holdings, so the watchlist has to carry the
        # fields the scrapers normally supply.
        watchlist = {
            k: [
                {
                    "ticker": f"T{i}",
                    "name": f"T{i} Ltd",
                    "price": "100.00",
                    "catalyst": "test catalyst",
                    "screener": {"pe_ratio": 20.0},
                }
            ]
            for i, k in enumerate(keys)
        }
        # Five eligible sectors against the minimal cap of two, so three are
        # dropped and the note must account for them.
        from emails.mailer import _CAPS_MINIMAL

        html = _render_email(data, watchlist, _CAPS_MINIMAL)
        assert "most-changed" in html
        assert "5 sectors" in html

        # Nothing dropped: no note, because there is nothing to account for.
        full = _render_email(data, watchlist, _CAPS_NORMAL)
        assert "most-changed" not in full
