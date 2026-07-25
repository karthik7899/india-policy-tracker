"""Tests for the derived-metric quality gate (analysis/data_quality.py)."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from analysis.data_quality import (  # noqa: E402
    INSUFFICIENT_DATA,
    OK,
    OUT_OF_BAND,
    REVENUE_GROWTH_BAND,
    classify,
    clean_series,
    is_trustworthy,
)


def test_clean_series_drops_unusable_entries_without_defaulting_to_zero():
    """A blank period must vanish, not become a zero.

    A zero would be treated as a real observation by every ratio downstream
    and would quietly halve a growth base.
    """
    assert clean_series(["1,200.5", "", None, "N/A", "300", "-"]) == [1200.5, 300.0]
    assert clean_series(None) == []
    assert clean_series([]) == []


def test_classify_requires_enough_observations():
    assert classify(10.0, observations=5, min_observations=8) == INSUFFICIENT_DATA
    assert classify(10.0, observations=8, min_observations=8) == OK


def test_classify_rejects_values_outside_the_band():
    assert classify(900.0, band=REVENUE_GROWTH_BAND) == OUT_OF_BAND
    assert classify(-99.0, band=REVENUE_GROWTH_BAND) == OUT_OF_BAND
    assert classify(40.0, band=REVENUE_GROWTH_BAND) == OK


def test_band_edges_are_inclusive():
    assert classify(REVENUE_GROWTH_BAND[0], band=REVENUE_GROWTH_BAND) == OK
    assert classify(REVENUE_GROWTH_BAND[1], band=REVENUE_GROWTH_BAND) == OK


def test_missing_value_is_never_trustworthy():
    assert classify(None) == INSUFFICIENT_DATA
    assert classify(None, band=REVENUE_GROWTH_BAND) == INSUFFICIENT_DATA


def test_only_ok_is_trustworthy():
    assert is_trustworthy(OK) is True
    assert is_trustworthy(OUT_OF_BAND) is False
    assert is_trustworthy(INSUFFICIENT_DATA) is False
    assert is_trustworthy(None) is False
