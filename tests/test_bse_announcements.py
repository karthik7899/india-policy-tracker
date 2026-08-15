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


def test_params_match_the_captured_request_exactly():
    """Captured from Chrome on the live page, not guessed:

      .../AnnSubCategoryGetData/w?pageno=1&strCat=-1&strPrevDate=20260815
        &strScrip=&strSearch=P&strToDate=20260815&strType=C&subcategory=-1

    Every field is pinned because thirty-two attempts sent these exact
    parameters to the wrong path, and a silent drift in either would put us
    back there."""
    import datetime

    day = datetime.date(2026, 8, 15)
    assert bse.announcement_params(day, day) == {
        "pageno": "1",
        "strCat": "-1",
        "strPrevDate": "20260815",
        "strScrip": "",
        "strSearch": "P",
        "strToDate": "20260815",
        "strType": "C",
        "subcategory": "-1",
    }


def test_the_endpoint_is_annsubcategorygetdata():
    """AnnGetData is alive and answers "No Record Found!" to this very query.
    It is the wrong door, and it fails quietly rather than loudly."""
    assert bse.ANNOUNCEMENTS_URL.endswith("/AnnSubCategoryGetData/w")


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
        Exception("apex refused"),
        Exception("disclosures frame refused"),
        _response(payload={"Table": [SAMPLE_RECORD]}),
    ]
    assert bse.fetch_announcements(session=session) == [SAMPLE_RECORD]


def test_handshake_visits_the_disclosures_frame_not_just_the_host():
    """The XHR is issued from ann.html, so that is the scope any cookie the
    API cares about is minted under."""
    session = MagicMock()
    session.cookies = {"x": "1"}
    session.get.return_value = _response(payload={"Table": []})
    assert bse.handshake(session) is True
    assert [c.args[0] for c in session.get.call_args_list] == [
        bse.HOME_URL,
        bse.REFERER_PAGE,
    ]


def test_api_headers_carry_referer_and_origin():
    """The API host is a different subdomain from the page the XHR comes
    from, so a browser sends both."""
    assert bse.API_HEADERS["Referer"] == "https://www.bseindia.com/"
    assert bse.API_HEADERS["Origin"] == "https://www.bseindia.com"


def test_the_referer_is_never_the_apex_form():
    """Measured: Referer: https://bseindia.com/ diverts EVERY endpoint on this
    host to /members/showinterest, including the scrip master, which had been
    returning 1.75 MB minutes earlier. Origin makes no difference either way.
    This is a one-character regression that silently kills all BSE access."""
    for value in (bse.API_HEADERS["Referer"], bse.HOME_URL, bse.REFERER_PAGE):
        assert value.startswith("https://www.bseindia.com")


# --- firewall interception ------------------------------------------------


def _redirected(landed, history=("https://bseindia.com/x",)):
    response = _response(payload={"Table": []})
    response.url = landed
    response.history = [MagicMock(url=u) for u in history]
    return response


def test_an_interstitial_redirect_is_an_intercept():
    session = MagicMock()
    session.get.return_value = _redirected(
        "https://www.bseindia.com/members/showinterest.aspx"
    )
    with pytest.raises(bse.BSEFirewallIntercept) as excinfo:
        bse._get(session, bse.ANNOUNCEMENTS_URL, {})
    assert "showinterest.aspx" in str(excinfo.value)


def test_a_redirect_off_the_domain_is_an_intercept():
    session = MagicMock()
    session.get.return_value = _redirected("https://errors.edgesuite.net/18.c50")
    with pytest.raises(bse.BSEFirewallIntercept):
        bse._get(session, bse.ANNOUNCEMENTS_URL, {})


def test_the_apex_to_www_hop_is_not_an_intercept():
    """We address the apex deliberately and BSE redirects apex -> www on every
    request. Treating that as an interception would mean the module never
    completes a call."""
    session = MagicMock()
    response = _redirected("https://www.bseindia.com/BseIndiaAPI/api/AnnGetData/w")
    response.json.return_value = {"Table": [SAMPLE_RECORD]}
    session.get.return_value = response
    assert bse._get(session, bse.ANNOUNCEMENTS_URL, {}) == [SAMPLE_RECORD]


def test_interception_is_checked_before_anything_parses():
    """An intercepted response can carry a 200 and a valid body, so every
    later check would pass while describing the wrong page."""
    session = MagicMock()
    response = _redirected("https://www.bseindia.com/members/login.aspx")
    session.get.return_value = response
    with pytest.raises(bse.BSEFirewallIntercept):
        bse._get(session, bse.ANNOUNCEMENTS_URL, {})
    response.json.assert_not_called()


# --- the Table contract ---------------------------------------------------


def test_missing_table_key_is_a_structural_failure():
    with pytest.raises(bse.BSEStructuralError) as excinfo:
        bse._validate_table({"SomethingElse": []})
    assert "STRUCTURAL FAILURE" in str(excinfo.value)
    assert "SomethingElse" in str(excinfo.value)


def test_empty_table_is_logged_not_raised():
    assert bse._validate_table({"Table": []}) == []


def test_table_holding_a_string_is_an_empty_result():
    assert bse._validate_table({"Table": "No Record Found!"}) == []


def test_table_holding_the_wrong_type_is_structural():
    with pytest.raises(bse.BSEStructuralError):
        bse._validate_table({"Table": {"not": "a list"}})


def test_the_scrip_master_is_not_held_to_the_table_contract():
    """It answers with a bare list. One contract for both endpoints would
    break whichever lost the argument."""
    assert bse._default_rows([{"SCRIP_CD": "1"}]) == [{"SCRIP_CD": "1"}]


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


# --- pagination -----------------------------------------------------------


def _page(n, total, count=2):
    return [
        {
            "SCRIP_CD": f"{n}{i}",
            "HEADLINE": f"page {n} item {i}",
            "TotalPageCnt": total,
        }
        for i in range(count)
    ]


def test_all_pages_are_read():
    """A full trading day runs to hundreds of announcements. A holding whose
    filing sits on page two is invisible to holdings-first ordering."""
    session = MagicMock()
    session.cookies = {"x": "1"}
    session.get.side_effect = [
        _response(payload={"Table": []}),  # handshake: apex
        _response(payload={"Table": []}),  # handshake: ann page
        _response(payload={"Table": _page(1, 3)}),
        _response(payload={"Table": _page(2, 3)}),
        _response(payload={"Table": _page(3, 3)}),
    ]
    rows = bse.fetch_announcements(session=session)
    assert len(rows) == 6
    assert [r["HEADLINE"] for r in rows][-1] == "page 3 item 1"


def test_pagination_is_capped():
    """An enrichment, not a crawl."""
    session = MagicMock()
    session.cookies = {"x": "1"}
    session.get.side_effect = [
        _response(payload={"Table": []}),
        _response(payload={"Table": []}),
    ] + [_response(payload={"Table": _page(n, 999)}) for n in range(1, 40)]

    rows = bse.fetch_announcements(session=session)
    assert len(rows) == bse.MAX_PAGES * 2


def test_a_single_page_makes_one_request():
    session = MagicMock()
    session.cookies = {"x": "1"}
    session.get.side_effect = [
        _response(payload={"Table": []}),
        _response(payload={"Table": []}),
        _response(payload={"Table": _page(1, 1)}),
    ]
    assert len(bse.fetch_announcements(session=session)) == 2


def test_a_missing_page_count_is_treated_as_one_page():
    """Undocumented like everything else here: a bad value must not turn a
    working fetch into a crash or a crawl."""
    assert bse._page_count([{"HEADLINE": "x"}]) == 1
    assert bse._page_count([{"TotalPageCnt": "not a number"}]) == 1
    assert bse._page_count([]) == 1
    assert bse._page_count([{"TotalPageCnt": 4}]) == 4
