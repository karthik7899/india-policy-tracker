import pytest
from utils import safe_float, safe_int, safe_percentage

def test_safe_float():
    assert safe_float(None) is None
    assert safe_float("") is None
    assert safe_float("-") is None
    assert safe_float("N/A") is None
    assert safe_float("NA") is None
    assert safe_float("123.45") == 123.45
    assert safe_float("1,234.56") == 1234.56
    assert safe_float(10) == 10.0
    assert safe_float("invalid") is None
    assert safe_float("invalid", default=0.0) == 0.0
    assert safe_float("", default=1.5) == 1.5

def test_safe_int():
    assert safe_int(None) is None
    assert safe_int("") is None
    assert safe_int("-") is None
    assert safe_int("N/A") is None
    assert safe_int("123") == 123
    assert safe_int("1,234") == 1234
    assert safe_int("123.45") == 123
    assert safe_int(10) == 10
    assert safe_int("invalid") is None
    assert safe_int("invalid", default=0) == 0
    assert safe_int("", default=-1) == -1

def test_safe_percentage():
    assert safe_percentage(None) is None
    assert safe_percentage("") is None
    assert safe_percentage("-") is None
    assert safe_percentage("N/A") is None
    assert safe_percentage("12.5%") == 12.5
    assert safe_percentage("1,234.5%") == 1234.5
    assert safe_percentage("12.5") == 12.5
    assert safe_percentage(10) == 10.0
    assert safe_percentage("invalid") is None
    assert safe_percentage("invalid", default=0.0) == 0.0
    assert safe_percentage("", default=0.0) == 0.0


import tempfile
import json
import os
from utils import atomic_write_json

def test_atomic_write_json():
    with tempfile.TemporaryDirectory() as tmpdir:
        target_file = os.path.join(tmpdir, 'test.json')
        data = {'key': 'value'}
        atomic_write_json(data, target_file)
        
        assert os.path.exists(target_file)
        with open(target_file, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
        assert loaded == data
