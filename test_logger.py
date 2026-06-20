import unittest
import logging
import sys
from logger import setup_logger


class TestLogger(unittest.TestCase):
    def setUp(self):
        # Clear handlers to ensure clean state before each test
        logging.getLogger().handlers.clear()
        logging.getLogger("bharat_policy").handlers.clear()

    def test_setup_logger_level(self):
        logger = setup_logger()
        # Both implementations set the logger level to INFO
        self.assertEqual(logger.level, logging.INFO)

    def test_setup_logger_handlers(self):
        logger = setup_logger()
        # Verify a handler was added
        self.assertEqual(len(logger.handlers), 1)

        handler = logger.handlers[0]
        # Verify it's a StreamHandler
        self.assertIsInstance(handler, logging.StreamHandler)
        # Verify it logs to stdout
        self.assertEqual(handler.stream, sys.stdout)

        # Verify formatting
        formatter = handler.formatter
        self.assertIsNotNone(formatter)
        self.assertEqual(formatter._fmt, "%(asctime)s - %(levelname)s - %(message)s")
        self.assertEqual(formatter.datefmt, "%Y-%m-%d %H:%M:%S")

    def test_setup_logger_multiple_calls(self):
        logger1 = setup_logger()
        logger2 = setup_logger()

        # Should be the same logger instance returned by getLogger
        self.assertIs(logger1, logger2)


if __name__ == "__main__":
    unittest.main()
