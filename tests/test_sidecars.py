"""Tests for the payload sidecar split (dashboard/sidecars.py).

The split moves 28% of the payload out of the file the browser downloads on
every load. What matters here is not that it saves bytes — that is arithmetic —
but that it cannot lose data, cannot write outside its directory, and cannot
take the run down when it fails. Each of those has a precedent in this repo.
"""

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dashboard import sidecars  # noqa: E402


def _payload():
    return {
        "stock_topics": {"HAL": [{"t": "a"}], "BEL": [{"t": "b"}]},
        "buffett_valuation": [{"ticker": "HAL"}, {"ticker": "BEL"}],
        "early_warnings": [],
        "sector_growth": [{"sector": "defence"}],
    }


def _run(tmp_path, payload=None):
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        return sidecars.write_sidecars(payload or _payload())
    finally:
        os.chdir(cwd)


# --- the split itself -----------------------------------------------------


def test_heavy_keys_become_manifests_not_data(tmp_path):
    light, written = _run(tmp_path)
    assert written == 3  # two tickers + one whole key

    assert light["stock_topics"] == {
        "sidecar": "data/stock_topics",
        "tickers": ["BEL", "HAL"],
    }
    assert light["buffett_valuation"] == {
        "sidecar": "data/buffett_valuation.json",
        "count": 2,
    }


def test_the_manifest_lists_tickers_so_the_browser_needs_no_round_trip(tmp_path):
    """A drawer must know whether a holding HAS a sidecar before fetching it.
    Without the list, a miss costs a 404 per holding to discover."""
    light, _ = _run(tmp_path)
    assert light["stock_topics"]["tickers"] == ["BEL", "HAL"]  # sorted, not dict order


def test_the_files_carry_the_data_that_left_the_payload(tmp_path):
    _run(tmp_path)
    with open(tmp_path / "data" / "stock_topics" / "HAL.json", encoding="utf-8") as f:
        assert json.load(f) == {"ticker": "HAL", "value": [{"t": "a"}]}
    with open(tmp_path / "data" / "buffett_valuation.json", encoding="utf-8") as f:
        assert json.load(f)["value"] == [{"ticker": "HAL"}, {"ticker": "BEL"}]


def test_untouched_keys_pass_through(tmp_path):
    light, _ = _run(tmp_path)
    assert light["sector_growth"] == [{"sector": "defence"}]


def test_the_callers_payload_is_not_mutated(tmp_path):
    """The same dict built the email and the corpus. Emptying a key it still
    reads is exactly the failure this repo keeps shipping."""
    original = _payload()
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        sidecars.write_sidecars(original)
    finally:
        os.chdir(cwd)
    assert original["stock_topics"] == {"HAL": [{"t": "a"}], "BEL": [{"t": "b"}]}
    assert original["buffett_valuation"] == [{"ticker": "HAL"}, {"ticker": "BEL"}]


# --- the three rules inherited from the coverage sidecars ------------------


def test_a_hostile_ticker_cannot_escape_the_directory(tmp_path):
    """The coverage sidecars have this exact test; the same input reaches
    here, because both are keyed on tickers from a scraped watchlist."""
    light, _ = _run(tmp_path, {"stock_topics": {"../../etc/passwd": [{"t": "x"}]}})
    written = os.listdir(tmp_path / "data" / "stock_topics")
    assert written == ["ETCPASSWD.json"]
    assert not (tmp_path.parent / "etc").exists()
    assert light["stock_topics"]["tickers"] == ["ETCPASSWD"]


def test_a_ticker_with_nothing_usable_is_skipped_not_written(tmp_path):
    light, written = _run(tmp_path, {"stock_topics": {"///": [{"t": "x"}]}})
    assert written == 0
    assert light["stock_topics"]["tickers"] == []


def test_stale_sidecars_are_removed(tmp_path):
    """A holding rotated out would otherwise serve its last figures forever."""
    _run(tmp_path, {"stock_topics": {"OLDCO": [{"t": "x"}]}})
    assert (tmp_path / "data" / "stock_topics" / "OLDCO.json").exists()

    _run(tmp_path, {"stock_topics": {"NEWCO": [{"t": "y"}]}})
    assert not (tmp_path / "data" / "stock_topics" / "OLDCO.json").exists()
    assert (tmp_path / "data" / "stock_topics" / "NEWCO.json").exists()


def test_a_write_failure_returns_the_payload_intact(tmp_path, monkeypatch):
    """Losing a sidecar costs a drawer. Losing the run costs the briefing."""
    import utils

    monkeypatch.setattr(
        utils, "atomic_write_json", lambda *a, **k: (_ for _ in ()).throw(OSError())
    )
    light, written = _run(tmp_path)
    assert written == 0
    # The data is still there — the caller ships a heavy payload, not a broken one.
    assert light["stock_topics"] == {"HAL": [{"t": "a"}], "BEL": [{"t": "b"}]}


# --- what is deliberately NOT split ---------------------------------------


def test_empty_keys_survive_the_split(tmp_path):
    """payload.py distinguishes a key that is absent (the step never ran) from
    one that is [] (it ran and found nothing). The seven empty keys in the real
    payload total ~14 bytes; they are information, not weight."""
    light, _ = _run(tmp_path)
    assert "early_warnings" in light
    assert light["early_warnings"] == []


def test_a_missing_heavy_key_is_not_invented(tmp_path):
    light, written = _run(tmp_path, {"sector_growth": []})
    assert "stock_topics" not in light
    assert "buffett_valuation" not in light
    assert written == 0


# --- sector de-duplication ------------------------------------------------


def test_a_fully_duplicated_sector_key_is_dropped():
    payload = {
        "sector_blocks": [{"news": [{"title": "Defence order win for HAL"}]}],
        "aerospace_defence": [{"title": "Defence order win for HAL"}],
    }
    assert sidecars.deduplicate_sector_news(payload, ["aerospace_defence"]) == 1
    assert "aerospace_defence" not in payload


def test_a_partly_duplicated_key_is_kept_whole():
    """A partial overlap means the key still carries something the blocks do
    not. Dropping it to save bytes would lose that item silently."""
    payload = {
        "sector_blocks": [{"news": [{"title": "Defence order win for HAL"}]}],
        "aerospace_defence": [
            {"title": "Defence order win for HAL"},
            {"title": "Something the blocks never saw"},
        ],
    }
    assert sidecars.deduplicate_sector_news(payload, ["aerospace_defence"]) == 0
    assert len(payload["aerospace_defence"]) == 2


def test_no_blocks_means_nothing_is_dropped():
    payload = {"aerospace_defence": [{"title": "x"}]}
    assert sidecars.deduplicate_sector_news(payload, ["aerospace_defence"]) == 0
    assert "aerospace_defence" in payload


def test_nothing_to_split_leaves_no_empty_directory(tmp_path):
    """An empty data/ implies there is data in it. A run with nothing to split
    must leave no trace — this also stopped the test suite creating the
    directory in the repo working tree on every run."""
    light, written = _run(tmp_path, {"sector_growth": []})
    assert written == 0
    assert not (tmp_path / "data").exists()
