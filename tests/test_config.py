import pytest
from unittest.mock import mock_open, patch
import json
import config

def test_save_watchlist_success():
    """Test that save_watchlist successfully opens a file and dumps JSON."""
    test_watchlist = {"AAPL": {"name": "Apple Inc."}}

    with patch("builtins.open", mock_open()) as mock_file:
        with patch("json.dump") as mock_json_dump:
            # Call the function
            config.save_watchlist(test_watchlist)

            # Verify builtins.open was called to write
            assert mock_file.called
            args, kwargs = mock_file.call_args
            assert args[1] == "w" or kwargs.get("mode") == "w"

            # Verify json.dump was called with the correct watchlist data
            assert mock_json_dump.called
            dump_args, _ = mock_json_dump.call_args
            assert dump_args[0] == test_watchlist

def test_save_watchlist_failure():
    """Test that save_watchlist handles file write exceptions gracefully."""
    test_watchlist = {"AAPL": {"name": "Apple Inc."}}

    # Mock builtins.open to simulate a failure
    with patch("builtins.open", side_effect=Exception("Disk full")):
        # The function should catch the exception and not raise it
        config.save_watchlist(test_watchlist)
