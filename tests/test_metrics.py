import pytest
from metrics import extract_ratio

def test_extract_ratio_happy_path():
    html = """
    <li class="flex flex-space-between">
        <span class="name">
        Market Cap
        </span>
        <span class="nowrap value">
        <span class="number">1,234.56</span>
        <span class="text">Cr.</span>
        </span>
    </li>
    """
    assert extract_ratio(html, "Market Cap") == "1234.56"

def test_extract_ratio_no_comma():
    html = """
    <li class="flex flex-space-between">
        <span class="name">
        Stock P/E
        </span>
        <span class="nowrap value">
        <span class="number">24.5</span>
        <span class="text"></span>
        </span>
    </li>
    """
    assert extract_ratio(html, "Stock P/E") == "24.5"

def test_extract_ratio_missing_label():
    html = """
    <li class="flex flex-space-between">
        <span class="name">
        Book Value
        </span>
        <span class="nowrap value">
        <span class="number">100.0</span>
        <span class="text"></span>
        </span>
    </li>
    """
    # Try looking for a label that doesn't exist
    assert extract_ratio(html, "Market Cap") is None

def test_extract_ratio_empty_html():
    assert extract_ratio("", "Market Cap") is None
    assert extract_ratio(None, "Market Cap") is None

def test_extract_ratio_malformed_html():
    html = """
    <li class="flex flex-space-between">
        <span class="name">
        Market Cap
        </span>
        <span class="nowrap value">
        <!-- missing number class -->
        <span>1,234.56</span>
        </span>
    </li>
    """
    assert extract_ratio(html, "Market Cap") is None

def test_extract_ratio_case_sensitive_label():
    # regex matches exactly the provided label so it is case sensitive by default in the original code,
    # let's verify that behavior.
    html = """
    <li class="flex flex-space-between">
        <span class="name">
        Market Cap
        </span>
        <span class="nowrap value">
        <span class="number">1,234.56</span>
        </span>
    </li>
    """
    assert extract_ratio(html, "Market cap") is None
