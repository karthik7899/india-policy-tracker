import unittest
from metrics import get_potential

class TestMetrics(unittest.TestCase):
    def test_get_potential_valid_string(self):
        stock = {"growth_pct": "15.5%"}
        self.assertEqual(get_potential(stock), 15.5)

    def test_get_potential_valid_string_with_plus(self):
        stock = {"growth_pct": "+20.0%"}
        self.assertEqual(get_potential(stock), 20.0)

    def test_get_potential_valid_float(self):
        stock = {"growth_pct": 10.5}
        self.assertEqual(get_potential(stock), 10.5)

    def test_get_potential_missing_key(self):
        stock = {}
        self.assertEqual(get_potential(stock), 0.0)

    def test_get_potential_invalid_string(self):
        stock = {"growth_pct": "invalid"}
        self.assertEqual(get_potential(stock), 0.0)

    def test_get_potential_none(self):
        stock = {"growth_pct": None}
        self.assertEqual(get_potential(stock), 0.0)

if __name__ == "__main__":
    unittest.main()
