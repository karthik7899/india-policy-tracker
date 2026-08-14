"""Tests for the NSE corporate-announcements provider.

The cases that matter here are the failure modes, not the happy path. NSE's
block arrives as HTML with a 200 status on it, and the whole point of the
provider is that this is caught as a network verdict rather than dying as a
parse error three layers down. Each check below pins one of those.
"""

import datetime
from unittest.mock import MagicMock, patch

import pytest
import requests

from providers import nse_announcements as nse


def _response(
    status=200, content_type="application/json", payload=None, text="", url=nse.API_URL
):
    """A requests.Response stand-in. Built by hand rather than with a library
    so the content-type and the body can disagree, which is exactly what a
    bot-challenge response does."""
    response = MagicMock()
    response.status_code = status
    response.headers = {"Content-Type": content_type}
    response.url = url
    response.text = text
    if payload is None:
        response.json.side_effect = ValueError("Expecting value: line 1 column 1")
    else:
        response.json.return_value = payload
    return response


SAMPLE_RECORD = {
    "symbol": "TATAMOTORS",
    "sm_name": "Tata Motors Limited",
    "desc": "Awarding of Order / Receipt of Order",
    "an_dt": "14-Aug-2026 17:30:00",
    "attchmntFile": "https://nsearchives.nseindia.com/corporate/TATAMOTORS_1.pdf",
}

WATCHLIST = {
    "Automotive": [{"ticker": "TATAMOTORS", "name": "Tata Motors"}],
}


@pytest.fixture(autouse=True)
def _no_sleeping():
    """The provider deliberately sleeps 2-5s between requests. Real in
    production, intolerable in a suite that runs in under two seconds."""
    with patch.object(nse.time, "sleep"):
        yield


# --- validation layers ---------------------------------------------------


def test_auth_status_raises_blocked_with_troubleshooting_context():
    with pytest.raises(nse.NSEBlockedError) as excinfo:
        nse._validate_http(_response(status=403))
    message = str(excinfo.value)
    # The message is the deliverable: from a CI log, a 403 is otherwise
    # indistinguishable from a bug in this file.
    assert "403" in message
    assert "handshake" in message
    assert "cloud range" in message


def test_transient_status_is_left_to_the_retry_decorator():
    from utils import TransientNetworkError

    with pytest.raises(TransientNetworkError):
        nse._validate_http(_response(status=503))


def test_ok_status_passes():
    assert nse._validate_http(_response(status=200)) is None


def test_html_body_with_200_is_caught_before_parsing():
    """The core defence. NSE serves its bot challenge as HTML with a 200."""
    response = _response(
        content_type="text/html; charset=utf-8",
        text="<html><body>Access Denied</body></html>",
    )
    with pytest.raises(nse.NSEContentTypeError) as excinfo:
        nse._validate_content_type(response)
    assert "text/html" in str(excinfo.value)
    # And it never reached the parser, which is what stops the misleading
    # JSONDecodeError.
    response.json.assert_not_called()


def test_missing_content_type_is_refused():
    with pytest.raises(nse.NSEContentTypeError):
        nse._validate_content_type(_response(content_type=""))


def test_undecodable_json_raises_schema_error():
    with pytest.raises(nse.NSESchemaError):
        nse._validate_schema(_response(payload=None))


def test_schema_accepts_bare_list_and_data_envelope():
    assert nse._validate_schema(_response(payload=[SAMPLE_RECORD])) == [SAMPLE_RECORD]
    assert nse._validate_schema(_response(payload={"data": [SAMPLE_RECORD]})) == [
        SAMPLE_RECORD
    ]


def test_schema_rejects_unexpected_top_level_type():
    with pytest.raises(nse.NSESchemaError):
        nse._validate_schema(_response(payload="a string"))
    with pytest.raises(nse.NSESchemaError):
        nse._validate_schema(_response(payload={"data": "not a list"}))


# --- normalisation -------------------------------------------------------


def test_normalize_maps_a_holding_to_the_filing_shape():
    out = nse.normalize(SAMPLE_RECORD, nse.build_symbol_index(WATCHLIST))
    assert out == {
        "company": "Tata Motors",
        "industry": "Automotive",
        "filing": "Awarding of Order / Receipt of Order",
        "date": "14 Aug 2026",
        "source": "NSE",
        "link": "https://nsearchives.nseindia.com/corporate/TATAMOTORS_1.pdf",
    }


def test_normalize_reads_through_field_aliases():
    """The field names the spec quotes ('an_date', 'attachment') differ from
    the ones NSE currently sends. Both must work, or a rename empties the
    feed silently."""
    out = nse.normalize(
        {
            "symbol": "TATAMOTORS",
            "subject": "Board Meeting Intimation",
            "an_date": "2026-08-14",
            "attachment": "https://example.test/f.pdf",
        },
        nse.build_symbol_index(WATCHLIST),
    )
    assert out["filing"] == "Board Meeting Intimation"
    assert out["date"] == "14 Aug 2026"
    assert out["link"] == "https://example.test/f.pdf"


def test_normalize_keeps_non_holdings_labelled_corporate():
    out = nse.normalize({"symbol": "XYZ", "desc": "Something"}, {})
    assert out["company"] == "XYZ"
    assert out["industry"] == "Corporate"


def test_normalize_drops_records_that_identify_nothing():
    assert nse.normalize({"desc": "No symbol here"}, {}) is None
    assert nse.normalize({"symbol": "ABC"}, {}) is None
    assert nse.normalize("not a dict", {}) is None


def test_unparseable_date_is_passed_through_not_invented():
    """Never fabricate: an odd date is information, a guessed one is not."""
    assert nse._parse_date("sometime last week") == "sometime last week"
    assert nse._parse_date("") == ""


def test_missing_attachment_falls_back_to_the_announcements_page():
    out = nse.normalize({"symbol": "ABC", "desc": "Update"}, {})
    assert out["link"] == nse.REFERER_PAGE


# --- handshake -----------------------------------------------------------


def test_handshake_reports_failure_when_no_cookies_are_set():
    session = MagicMock()
    session.get.return_value = _response(status=200)
    session.cookies = {}
    assert nse.handshake(session) is False


def test_handshake_succeeds_when_cookies_arrive():
    session = MagicMock()
    session.get.return_value = _response(status=200)
    session.cookies = {"nsit": "abc"}
    assert nse.handshake(session) is True
    # Home page AND the announcements page, in that order — the API checks
    # the Referer, and a session that never visited it is refused.
    assert [c.args[0] for c in session.get.call_args_list] == [
        nse.HOME_URL,
        nse.REFERER_PAGE,
    ]


def test_handshake_survives_a_connection_error():
    session = MagicMock()
    session.get.side_effect = requests.ConnectionError("no route")
    assert nse.handshake(session) is False


# --- end to end ----------------------------------------------------------


def test_fetch_filings_returns_normalized_records():
    with patch.object(nse, "fetch_announcements", return_value=[SAMPLE_RECORD]):
        out = nse.fetch_filings(WATCHLIST)
    assert len(out) == 1
    assert out[0]["company"] == "Tata Motors"


def test_fetch_filings_never_raises_when_nse_blocks():
    """The pipeline-facing guarantee: a blocked exchange degrades the filings
    section, it does not end the briefing."""
    with patch.object(
        nse, "fetch_announcements", side_effect=nse.NSEBlockedError("403")
    ):
        assert nse.fetch_filings(WATCHLIST) == []


def test_fetch_filings_swallows_unexpected_errors_too():
    with patch.object(nse, "fetch_announcements", side_effect=RuntimeError("boom")):
        assert nse.fetch_filings(WATCHLIST) == []


def test_fetch_announcements_sends_the_date_window_nse_expects():
    session = MagicMock()
    session.cookies = {"nsit": "abc"}
    session.get.return_value = _response(payload=[SAMPLE_RECORD])

    day = datetime.date(2026, 8, 14)
    nse.fetch_announcements(session=session, from_date=day, to_date=day)

    api_call = [c for c in session.get.call_args_list if c.args[0] == nse.API_URL][0]
    assert api_call.kwargs["params"] == {
        "index": "equities",
        "from_date": "14-08-2026",
        "to_date": "14-08-2026",
    }
    # Referer is load-bearing, not decoration.
    assert api_call.kwargs["headers"]["Referer"] == nse.REFERER_PAGE


def test_fetch_announcements_reestablishes_the_session_after_a_block():
    """A 403 usually means stale cookies, so a second handshake is worth one
    attempt — but the retry is bounded and the error still surfaces."""
    session = MagicMock()
    session.cookies = {"nsit": "abc"}
    session.get.return_value = _response(status=403)

    with pytest.raises(nse.NSEBlockedError):
        nse.fetch_announcements(session=session, handshakes=2)

    api_calls = [c for c in session.get.call_args_list if c.args[0] == nse.API_URL]
    assert len(api_calls) == 2


def test_defaults_to_today():
    session = MagicMock()
    session.cookies = {"nsit": "abc"}
    session.get.return_value = _response(payload=[])

    nse.fetch_announcements(session=session)

    today = datetime.date.today().strftime("%d-%m-%Y")
    api_call = [c for c in session.get.call_args_list if c.args[0] == nse.API_URL][0]
    assert api_call.kwargs["params"]["from_date"] == today
