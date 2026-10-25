"""Fixtures every test gets."""

import pytest

from analysis import reader_runtime


@pytest.fixture(autouse=True)
def _a_new_reader_run():
    """Each test is a run of its own: no model that answered or failed in
    another test orders this one's chains (analysis/reader_runtime.Run)."""
    reader_runtime.reset_run()
    yield
    reader_runtime.reset_run()
