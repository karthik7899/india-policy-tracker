"""Tests for the BSE corporate-announcements provider.

BSE differs from NSE in two ways that are easy to regress and expensive to
notice: its API does not need the cookie handshake (so a handshake failure
must not stop the call), and it keys everything by numeric scrip code rather
than ticker (so holdings resolve through ISIN, or not at all).
"""

from unittest.mock import MagicMock, patch

import pytest

from providers import bse_announcements as bse
from providers import exchange_api


def _response(status=200, content_type="application/json", payload=None, text=""):
    response = MagicMock()
    response.status_code = status
    response.headers = {"Content-Type": content_type}
    response.url = bse.ANNOUNCEMENTS_URL
    response.text = text
    if payload is None:
        response.json.side_effect = ValueError("Expecting value: line 1 column 1")
    else:
        response.json.return_value = payload
    return response


SAMPLE_RECORD = {
    "SCRIP_CD": "500325",
    "SLONGNAME": "Reliance Industries Ltd",
    "HEADLINE": "Reliance Industries Ltd has informed the Exchange about "
    "receipt of an order.",
    "NEWSSUB": "Company Update",
    "NEWS_DT": "2026-08-14T15:41:54.000Z",
    "ATTACHMENTNAME": "abc123.pdf",
    "CATEGORYNAME": "Company Update",
}

WATCHLIST = {
    "Energy": [
        {
            "ticker": "RELIANCE",
            "name": "Reliance Industries",
            "screener": {"isin": "INE002A01018"},
        }
    ]
}


@pytest.fixture(autouse=True)
def _no_sleeping():
    with patch.object(exchange_api.time, "sleep"):
        yield


# --- parameters ----------------------------------------------------------


def test_params_carry_every_field_bses_own_page_sends():
    """Earlier probes omitted subcategory and got "No Record Found!" for a
    window that certainly had filings in it."""
    import datetime

    day = datetime.date(2026, 8, 14)
    params = bse.announcement_params(day, day)
    assert params == {
        "pageno": "1",
        "strCat": "-1",
        "strPrevDate": "20260814",
        "strToDate": "20260814",
        "strScrip": "",
        "strSearch": "P",
        "strType": "C",
        "subcategory": "-1",
    }


# --- validation ----------------------------------------------------------


def test_the_table_envelope_is_unwrapped():
    """BSE wraps rows in Table, with a row count alongside in Table1."""
    session = MagicMock()
    session.get.return_value = _response(
        payload={"Table": [SAMPLE_RECORD], "Table1": [{"ROWCNT": 1}]}
    )
    assert bse._get(session, bse.ANNOUNCEMENTS_URL, {}) == [SAMPLE_RECORD]


def test_no_record_found_is_an_empty_result_not_an_error():
    """The endpoint is alive and the query matched nothing. That is a miss to
    log, not an exception to raise."""
    session = MagicMock()
    session.get.return_value = _response(payload={"Table": "No Record Found!"})
    assert bse._get(session, bse.ANNOUNCEMENTS_URL, {}) == []


def test_html_body_with_200_is_caught_before_parsing():
    session = MagicMock()
    session.get.return_value = _response(
        content_type="text/html", text="<html>Access Denied</html>"
    )
    with pytest.raises(bse.BSEContentTypeError):
        bse._get(session, bse.ANNOUNCEMENTS_URL, {})


def test_auth_status_raises_blocked_with_context():
    session = MagicMock()
    session.get.return_value = _response(status=403)
    with pytest.raises(bse.BSEBlockedError) as excinfo:
        bse._get(session, bse.ANNOUNCEMENTS_URL, {})
    assert "403" in str(excinfo.value)
    assert "Referer" in str(excinfo.value)


# --- handshake is best-effort, unlike NSE --------------------------------


def test_a_failed_handshake_does_not_stop_the_call():
    """The measured difference from NSE: api.bseindia.com has served us with
    no cookies at all, so a handshake failure must not be fatal."""
    session = MagicMock()
    session.cookies = {}
    session.get.side_effect = [
        Exception("home page refused"),
        _response(payload={"Table": [SAMPLE_RECORD]}),
    ]
    assert bse.fetch_announcements(session=session) == [SAMPLE_RECORD]


# --- normalisation -------------------------------------------------------


def test_normalize_maps_a_holding_to_the_filing_shape():
    out = bse.normalize(SAMPLE_RECORD, {"500325": ("Reliance Industries", "Energy")})
    assert out == {
        "company": "Reliance Industries",
        "industry": "Energy",
        "filing": "Reliance Industries Ltd has informed the Exchange about "
        "receipt of an order.",
        "date": "14 Aug 2026",
        "source": "BSE",
        "link": "https://www.bseindia.com/xml-data/corpfiling/AttachLive/abc123.pdf",
    }


def test_headline_beats_the_newssub_category():
    """Same trap NSE's `desc` turned out to be: the category is not a subject,
    and reading it renders every filing identically."""
    out = bse.normalize(SAMPLE_RECORD, {})
    assert out["filing"].startswith("Reliance Industries Ltd has informed")
    assert out["filing"] != "Company Update"


def test_a_full_url_attachment_is_left_alone():
    out = bse.normalize(
        {"SCRIP_CD": "1", "HEADLINE": "x", "ATTACHMENTNAME": "https://e.test/a.pdf"},
        {},
    )
    assert out["link"] == "https://e.test/a.pdf"


def test_missing_attachment_falls_back_to_the_announcements_page():
    out = bse.normalize({"SCRIP_CD": "1", "HEADLINE": "x"}, {})
    assert out["link"] == bse.REFERER_PAGE


def test_unparseable_date_is_passed_through_not_invented():
    assert bse._parse_date("whenever") == "whenever"
    assert bse._parse_date("") == ""


def test_records_identifying_nothing_are_dropped():
    assert bse.normalize({"HEADLINE": "no scrip"}, {}) is None
    assert bse.normalize({"SCRIP_CD": "1"}, {}) is None
    assert bse.normalize("not a dict", {}) is None


def test_long_subjects_are_trimmed_visibly():
    out = bse.normalize({"SCRIP_CD": "1", "HEADLINE": "x" * 400}, {})
    assert len(out["filing"]) == bse._MAX_SUBJECT_CHARS
    assert out["filing"].endswith("…")


# --- the ISIN join -------------------------------------------------------


def test_scrip_index_joins_holdings_through_isin():
    """BSE speaks scrip codes and the watchlist speaks NSE symbols; the scrip
    master is the only thing connecting them."""
    session = MagicMock()
    session.get.return_value = _response(
        payload=[
            {"SCRIP_CD": "500325", "ISIN_NUMBER": "INE002A01018"},
            {"SCRIP_CD": "999999", "ISIN_NUMBER": "INE999Z01011"},
        ]
    )
    index = bse.build_scrip_index(WATCHLIST, session=session)
    assert index == {"500325": ("Reliance Industries", "Energy")}


def test_scrip_index_is_empty_when_no_holding_has_an_isin():
    session = MagicMock()
    index = bse.build_scrip_index({"Energy": [{"ticker": "X", "name": "X"}]}, session)
    assert index == {}
    # And it did not spend a request finding that out.
    session.get.assert_not_called()


def test_scrip_index_degrades_to_empty_rather_than_raising():
    session = MagicMock()
    session.get.side_effect = Exception("scrip master down")
    assert bse.build_scrip_index(WATCHLIST, session=session) == {}


# --- end to end ----------------------------------------------------------


def test_fetch_filings_never_raises_when_bse_blocks():
    with patch.object(bse, "build_scrip_index", return_value={}), patch.object(
        bse, "fetch_announcements", side_effect=bse.BSEBlockedError("403")
    ):
        assert bse.fetch_filings(WATCHLIST) == []


def test_fetch_filings_swallows_unexpected_errors_too():
    with patch.object(bse, "build_scrip_index", return_value={}), patch.object(
        bse, "fetch_announcements", side_effect=RuntimeError("boom")
    ):
        assert bse.fetch_filings(WATCHLIST) == []


def test_holdings_are_sorted_ahead_of_everyone_else():
    others = [
        {"SCRIP_CD": str(900000 + i), "HEADLINE": f"Filing {i}"} for i in range(12)
    ]
    with patch.object(
        bse, "build_scrip_index", return_value={"500325": ("Reliance", "Energy")}
    ), patch.object(bse, "fetch_announcements", return_value=others + [SAMPLE_RECORD]):
        out = bse.fetch_filings(WATCHLIST)

    assert out[0]["company"] == "Reliance"
    assert [f["filing"] for f in out[1:3]] == ["Filing 0", "Filing 1"]


def test_no_record_found_arrives_as_a_bare_string():
    """Measured: BSE's empty answer is an 18-byte body parsing to the str
    "No Record Found!", not an envelope. Guarding only for a dict turned a
    routine reply into a schema error."""
    session = MagicMock()
    session.get.return_value = _response(payload="No Record Found!")
    assert bse._get(session, bse.ANNOUNCEMENTS_URL, {}) == []


def test_the_isin_join_is_skipped_when_there_is_nothing_to_name():
    """The scrip master costs 1.75 MB. AnnGetData answers "No Record Found!"
    to every parameter set tried so far, so paying for it up front would buy
    nothing on most days."""
    with patch.object(bse, "fetch_announcements", return_value=[]), patch.object(
        bse, "build_scrip_index"
    ) as index:
        assert bse.fetch_filings(WATCHLIST) == []
    index.assert_not_called()
