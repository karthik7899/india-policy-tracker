import pytest
from metrics import get_potential

def test_get_potential_with_percent_string():
    stock = {"growth_pct": "15.5%"}
    assert get_potential(stock) == 15.5

def test_get_potential_with_plus_percent_string():
    stock = {"growth_pct": "+20.0%"}
    assert get_potential(stock) == 20.0

def test_get_potential_with_float():
    stock = {"growth_pct": 12.5}
    assert get_potential(stock) == 12.5

def test_get_potential_with_missing_key():
    stock = {"name": "TestCorp"}
    assert get_potential(stock) == 0.0

def test_get_potential_with_invalid_string():
    stock = {"growth_pct": "invalid"}
    assert get_potential(stock) == 0.0

def test_get_potential_with_empty_string():
    stock = {"growth_pct": ""}
    assert get_potential(stock) == 0.0

def test_get_potential_with_none():
    stock = {"growth_pct": None}
    assert get_potential(stock) == 0.0
