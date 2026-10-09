"""Decisions sent from the dashboard (scripts/dashboard_actions.py).

The request arrives as an issue body anyone could have typed, so the tests
lean on what it must refuse: an unknown ticker, a sector that does not
exist, a stance that is not a stance, a proposal already decided. Each is
skipped and named, never guessed at.
"""

import json
import os
import shutil
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import dashboard_actions as da  # noqa: E402


@pytest.fixture
def repo(tmp_path):
    """The files a request can touch, copied so a test can change them."""
    for rel in (
        "watchlist.json",
        "entity_graph_proposals.json",
        *da.LABEL_FILES.values(),
    ):
        os.makedirs(tmp_path / os.path.dirname(rel), exist_ok=True)
        shutil.copy(os.path.join(ROOT, rel), tmp_path / rel)
    proposals = json.loads((tmp_path / "entity_graph_proposals.json").read_text())
    proposals["proposals"].insert(
        0,
        {
            "holding": "TCS",
            "counterparty": "Nordea Bank",
            "proposed_as": "Nordea Bank",
            "status": "pending",
            "first_seen": "2026-10-08",
            "last_seen": "2026-10-08",
            "evidence": [
                {"headline": "TCS and Nordea Bank form JV", "date": "2026-10-08"}
            ],
        },
    )
    (tmp_path / "entity_graph_proposals.json").write_text(json.dumps(proposals))
    return tmp_path


def _labels(repo, kind):
    return json.loads((repo / da.LABEL_FILES[kind]).read_text())["labels"]


def _where(repo):
    w = json.loads((repo / "watchlist.json").read_text())
    return {
        s["ticker"]: (sector, s.get("sector_confirmed"))
        for sector, stocks in w.items()
        if sector != "macro_indicators"
        for s in stocks
        if isinstance(s, dict)
    }


# ---------------------------------------------------------------------------
# the id both sides compute
# ---------------------------------------------------------------------------


def test_row_ids_match_the_browser():
    """The same vectors are pinned in tests/frontend/review.test.mjs."""
    assert da.fnv1a("") == "811c9dc5"
    assert da.fnv1a("a") == "e40c292c"
    assert (
        da.fnv1a("Dixon eyes product portfolio expansion, scouts new facility")
        == "c572abdd"
    )
    assert da.fnv1a("Lakmē ₹") == "34fec48c"
    row = {
        "ticker": "SIEMENS",
        "headline": "Siemens unveils ÖBB Railjet M at InnoTrans",
    }
    assert da.row_id("thesis", row) == "5441d511"


# ---------------------------------------------------------------------------
# reading the request
# ---------------------------------------------------------------------------


def _body(payload):
    return (
        "Decisions from the dashboard.\n\n<!-- tracker:decisions v1 -->\n```json\n"
        + json.dumps(payload)
        + "\n```"
    )


def test_an_issue_without_the_marker_is_not_ours():
    assert da.parse_request("Please add HAL to the watchlist") == (None, None, "")


def test_a_request_that_does_not_parse_is_reported():
    kind, payload, error = da.parse_request(
        "<!-- tracker:decisions v1 -->\n```json\n{not json}\n```"
    )
    assert kind == "decisions" and payload is None and "does not parse" in error
    _, _, error = da.parse_request(_body({"v": 2}))
    assert "version 1" in error


# ---------------------------------------------------------------------------
# partners
# ---------------------------------------------------------------------------


def test_a_partner_is_accepted_under_the_corrected_name(repo):
    report = da.apply_decisions(
        {
            "v": 1,
            "proposals": [
                {
                    "holding": "TCS",
                    "proposed_as": "Nordea Bank",
                    "status": "accepted",
                    "counterparty": "Nordea",
                }
            ],
        },
        root=str(repo),
    )
    assert report["skipped"] == []
    p = json.loads((repo / "entity_graph_proposals.json").read_text())["proposals"]
    nordea = next(x for x in p if x["proposed_as"] == "Nordea Bank")
    assert (nordea["status"], nordea["counterparty"]) == ("accepted", "Nordea")


def test_partner_requests_that_do_not_fit_are_skipped(repo):
    report = da.apply_decisions(
        {
            "v": 1,
            "proposals": [
                {"holding": "TCS", "proposed_as": "Nordea Bank", "status": "maybe"},
                {"holding": "TCS", "proposed_as": "Nobody", "status": "rejected"},
                # Decided in the first review; a decision is not reopened here.
                {"holding": "TCS", "proposed_as": "DGCX", "status": "accepted"},
            ],
        },
        root=str(repo),
    )
    assert report["applied"] == []
    assert len(report["skipped"]) == 3
    assert any("already rejected" in s for s in report["skipped"])


# ---------------------------------------------------------------------------
# sector placement
# ---------------------------------------------------------------------------


def test_a_holding_moves_or_is_kept_and_stops_being_flagged(repo):
    from analysis.sector_fit import audit_watchlist

    report = da.apply_decisions(
        {
            "v": 1,
            "moves": [
                {"ticker": "OFSS", "to": "midcap_it"},
                {"ticker": "ADANIPOWER", "keep": True},
            ],
        },
        root=str(repo),
    )
    assert report["skipped"] == []
    where = _where(repo)
    assert where["OFSS"] == ("midcap_it", None)
    assert where["ADANIPOWER"] == ("clean_energy", "clean_energy")
    audit = audit_watchlist(json.loads((repo / "watchlist.json").read_text()))
    flagged = {m["ticker"] for m in audit["misfits"]}
    assert "ADANIPOWER" not in flagged and "ADANIPOWER" in audit["confirmed"]


def test_a_kept_holding_moved_later_is_checked_again():
    from analysis.sector_fit import audit_watchlist

    stock = {
        "ticker": "ADANIPOWER",
        "yahoo_industry": "Utilities - Independent Power Producers",
        "business_keywords": [],
        "sector_confirmed": "clean_energy",
    }
    audit = audit_watchlist({"semiconductors_equipment": [stock]})
    assert audit["confirmed"] == []


def test_moves_that_do_not_fit_are_skipped(repo):
    report = da.apply_decisions(
        {
            "v": 1,
            "moves": [
                {"ticker": "NOSUCH", "to": "midcap_it"},
                {"ticker": "OFSS", "to": "not_a_sector"},
                {"ticker": "OFSS", "to": "macro_indicators"},
                {"ticker": "OFSS", "to": "cybersecurity"},
            ],
        },
        root=str(repo),
    )
    assert report["applied"] == []
    assert len(report["skipped"]) == 4
    assert _where(repo)["OFSS"][0] == "cybersecurity"


# ---------------------------------------------------------------------------
# labels
# ---------------------------------------------------------------------------


def test_labels_are_confirmed_and_corrected_by_id(repo):
    thesis = _labels(repo, "thesis")
    policy = _labels(repo, "policy")
    event = _labels(repo, "event")
    report = da.apply_decisions(
        {
            "v": 1,
            "labels": {
                "thesis": [
                    {"id": da.row_id("thesis", thesis[0]), "ok": True},
                    {
                        "id": da.row_id("thesis", thesis[1]),
                        "stance": "supports",
                        "about": False,
                        "note": "  read  it again ",
                    },
                ],
                "policy": [
                    {
                        "id": da.row_id("policy", policy[0]),
                        "is_policy": False,
                        "effects": [],
                    }
                ],
                "event": [
                    {
                        "id": da.row_id("event", event[0]),
                        "event_type": None,
                        "actors": ["DIXON"],
                        "counterparties": [],
                    }
                ],
            },
        },
        root=str(repo),
    )
    assert report["skipped"] == []
    t = _labels(repo, "thesis")
    assert t[0]["reviewed"] and t[0]["stance"] == thesis[0]["stance"]
    assert (t[1]["stance"], t[1]["about"], t[1]["note"]) == (
        "supports",
        False,
        "read it again",
    )
    p = _labels(repo, "policy")
    assert (p[0]["is_policy"], p[0]["effects"]) == (False, [])
    e = _labels(repo, "event")
    assert e[0]["event_type"] is None and e[0]["reviewed"]
    # The files keep their hand-edited shape.
    assert (repo / da.LABEL_FILES["thesis"]).read_text().endswith("}\n")


def test_label_corrections_that_do_not_fit_are_skipped(repo):
    thesis = _labels(repo, "thesis")
    policy = _labels(repo, "policy")
    event = _labels(repo, "event")
    report = da.apply_decisions(
        {
            "v": 1,
            "labels": {
                "thesis": [
                    {"id": da.row_id("thesis", thesis[0]), "stance": "loves it"},
                    {"id": "00000000", "ok": True},
                ],
                "policy": [
                    {
                        "id": da.row_id("policy", policy[0]),
                        "effects": [{"sector": "atlantis", "direction": "tailwind"}],
                    }
                ],
                "event": [
                    {"id": da.row_id("event", event[0]), "event_type": "alien_landing"},
                    {"id": da.row_id("event", event[1]), "actors": ["not a ticker"]},
                ],
                "elsewhere": [{"id": "x"}],
            },
        },
        root=str(repo),
    )
    assert report["applied"] == []
    assert len(report["skipped"]) == 6
    assert _labels(repo, "thesis") == thesis


def test_the_file_counts_as_reviewed_once_every_row_is():
    """A two-row file, both confirmed, says so at the top."""
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "eval"))
        rows = [
            {"headline": "a", "is_policy": False},
            {"headline": "b", "is_policy": False},
        ]
        with open(os.path.join(d, da.LABEL_FILES["policy"]), "w") as f:
            json.dump({"reviewed": False, "labels": rows}, f)
        da.apply_labels(
            {"policy": [{"id": da.row_id("policy", r), "ok": True} for r in rows]},
            d,
            {"applied": [], "skipped": []},
        )
        with open(os.path.join(d, da.LABEL_FILES["policy"])) as f:
            assert json.load(f)["reviewed"] is True


# ---------------------------------------------------------------------------
# the workflow
# ---------------------------------------------------------------------------


def test_decisions_wait_for_a_running_daily_briefing(monkeypatch):
    states = iter([True, True, False])
    monkeypatch.setattr(da, "daily_run_active", lambda: next(states))
    monkeypatch.setattr(da.time, "sleep", lambda s: None)
    assert da.wait_for_daily(limit_s=600, step_s=30) is True

    monkeypatch.setattr(da, "daily_run_active", lambda: True)
    assert da.wait_for_daily(limit_s=60, step_s=30) is False


def test_the_workflow_acts_only_for_the_owner_and_never_shells_the_body():
    """Anyone can open an issue on a public repository, and this job can write
    to it. Both guards are what make that safe; losing either is a hole."""
    with open(os.path.join(ROOT, ".github/workflows/dashboard-actions.yml")) as f:
        text = f.read()
    assert "author_association == 'OWNER'" in text
    assert "github.event.issue.body }}" not in text
    assert "github.event.issue.title }}" not in text
