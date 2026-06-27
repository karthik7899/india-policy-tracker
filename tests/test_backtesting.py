import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from analysis.backtesting import (  # noqa: E402
    classify_theme,
    _parse_nav_records,
    _to_iso_date,
    compute_accumulation_baseline,
    build_institutional_baseline,
)


def test_classify_theme():
    assert (
        classify_theme("ICICI Pru Nifty India Manufacturing ETF")
        == "Manufacturing & PLI"
    )
    assert classify_theme("HDFC Defence Fund - Direct Growth") == "Defence & Aerospace"
    assert (
        classify_theme("Motilal Oswal Semiconductor Index Fund")
        == "Semiconductors & Tech"
    )
    assert classify_theme("Some Large Cap Bluechip Fund") is None
    assert classify_theme("") is None


def test_to_iso_date_accepts_both_formats():
    assert _to_iso_date("05-03-2026") == "2026-03-05"
    assert _to_iso_date("2026-03-05") == "2026-03-05"
    assert _to_iso_date("garbage") is None


def test_parse_nav_records_sorts_and_filters():
    raw = [
        {"date": "03-01-2026", "nav": "12.50"},
        {"date": "01-01-2026", "nav": "12.00"},
        {"date": "02-01-2026", "nav": "bad"},  # dropped
        {"date": "", "nav": "9.0"},  # dropped
        {"date": "04-01-2026", "nav": "-1"},  # dropped (non-positive)
    ]
    records = _parse_nav_records(raw)
    assert records == [("2026-01-01", 12.0), ("2026-01-03", 12.5)]


def _series(values):
    # Oldest -> newest synthetic daily NAV series.
    return [
        (f"2026-{1 + i // 28:02d}-{1 + i % 28:02d}", v) for i, v in enumerate(values)
    ]


def test_compute_accumulation_baseline_accelerating():
    # Flat for a year then a sharp recent ramp -> 3M pace outruns the 1Y pace.
    values = [100.0] * 200 + [100.0 + i * 2 for i in range(1, 70)]
    metrics = compute_accumulation_baseline(_series(values))
    assert metrics is not None
    assert metrics["accumulation_trend"] == "Accelerating"
    assert metrics["return_1y"] is not None
    assert metrics["observations"] == len(values)


def test_compute_accumulation_baseline_decelerating():
    # Strong early gains then a recent plateau -> recent pace below 1Y pace.
    values = [100.0 + i for i in range(200)] + [300.0] * 69
    metrics = compute_accumulation_baseline(_series(values))
    assert metrics is not None
    assert metrics["accumulation_trend"] == "Decelerating"


def test_compute_accumulation_baseline_insufficient_data():
    assert compute_accumulation_baseline([]) is None
    assert compute_accumulation_baseline([("2026-01-01", 10.0)]) is None


def test_build_institutional_baseline_is_resilient_offline(monkeypatch):
    # With no reachable data source, the pipeline must get an empty list, not raise.
    import analysis.backtesting as bt

    monkeypatch.setattr(bt, "_http_get_json", lambda session, url: None)
    assert build_institutional_baseline() == []


def test_build_institutional_baseline_end_to_end(monkeypatch):
    import analysis.backtesting as bt

    ramp = [100.0] * 200 + [100.0 + i * 2 for i in range(1, 70)]
    # DD-MM-YYYY rows, as both mfapi.in and the captn3m0 CSV export provide.
    nav_data = [
        {"date": f"{1 + i % 28:02d}-{1 + i // 28:02d}-2026", "nav": str(v)}
        for i, v in enumerate(ramp)
    ]

    def fake_get(session, url):
        if url.endswith("/mf"):
            return [{"schemeCode": 1, "schemeName": "ABC Manufacturing Fund"}]
        return {"data": nav_data}

    monkeypatch.setattr(bt, "_http_get_json", fake_get)
    result = build_institutional_baseline(max_per_theme=1)
    assert len(result) == 1
    assert result[0]["theme"] == "Manufacturing & PLI"
    assert result[0]["fund_name"] == "ABC Manufacturing Fund"
    assert result[0]["accumulation_trend"] == "Accelerating"
