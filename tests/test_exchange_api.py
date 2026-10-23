import unittest
from providers.exchange_api import build_session


class TestExchangeAPI(unittest.TestCase):
    def test_build_session_tls_verification(self):
        """Test that TLS verification is explicitly enabled in the session."""
        session = build_session()
        self.assertTrue(session.verify)


if __name__ == "__main__":
    unittest.main()
