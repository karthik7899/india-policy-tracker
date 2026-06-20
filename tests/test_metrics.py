import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from metrics import _get_potential  # noqa: E402


def test_get_potential_valid_percentage():
    """Test valid percentage string with % sign."""
    assert _get_potential({"growth_pct": "15%"}) == 15.0
    assert _get_potential({"growth_pct": "15.5%"}) == 15.5


def test_get_potential_without_percentage():
    """Test valid percentage string without % sign."""
    assert _get_potential({"growth_pct": "15"}) == 15.0


def test_get_potential_negative():
    """Test negative percentage string."""
    assert _get_potential({"growth_pct": "-5%"}) == -5.0


def test_get_potential_missing_key():
    """Test missing growth_pct key returns 0.0."""
    assert _get_potential({}) == 0.0


def test_get_potential_invalid_value():
    """Test invalid string returns 0.0."""
    assert _get_potential({"growth_pct": "invalid"}) == 0.0


def test_get_potential_none_value():
    """Test None value returns 0.0."""
    assert _get_potential({"growth_pct": None}) == 0.0
