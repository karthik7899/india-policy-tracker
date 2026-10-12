import os  # noqa: E402
import sys  # noqa: E402

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scraper import _extract_pli_data_from_html  # noqa: E402


def test_extract_companies_from_pib_html():
    sample_html = """
    <html>
    <head><title>75 companies approved under PLI Scheme for Automobile</title></head>
    <body>
        <p>The government has provisionally selected the following companies:</p>
        <table>
            <tr><th>Company Name</th><th>Approval Date</th></tr>
            <tr><td>Tata Motors Ltd</td><td>2023-01-01</td></tr>
            <tr><td>Mahindra & Mahindra</td><td>2023-01-01</td></tr>
        </table>
        <ul>
            <li>TVS Motor Company Limited</li>
            <li>Hero MotoCorp</li>
        </ul>
    </body>
    </html>
    """
    companies = _extract_pli_data_from_html(
        sample_html,
        "75 companies approved under PLI Scheme for Automobile",
        "2023-10-10",
    )
    assert len(companies) >= 4
    names = [c["name"] for c in companies]
    assert "Tata Motors Ltd" in names
    assert "Mahindra & Mahindra" in names
    assert "TVS Motor Company Limited" in names
    assert "Hero MotoCorp" in names

    assert companies[0]["sector"] == "Automobile"
    assert companies[0]["scheme"] == "PLI Scheme"
    assert companies[0]["date"] == "2023-10-10"


# --- the scraper end to end, with no network ---------------------------------

import asyncio  # noqa: E402
import logging  # noqa: E402

import scraper  # noqa: E402

GOOGLE_PAGE = (
    "<html><head><title>Google News</title></head><body>"
    "<ul><li>Top stories</li><li>For you</li><li>Following</li></ul>"
    "</body></html>"
)
PIB_RELEASE = (
    "<html><head><title>Press Release: Press Information Bureau</title></head>"
    "<body><ul class='menu'><li><a href='/'>Home</a></li>"
    "<li><a href='/m'>Ministry of Steel</a></li></ul>"
    "<p>Press Information Bureau, Government of "
    "India</p><table><tr><th>Company Name</th></tr>"
    "<tr><td>Acme Electronics Ltd</td></tr>"
    "<tr><td>Zenith Drone Systems</td></tr></table></body></html>"
)


def _rss(*items):
    body = "".join(
        f"<item><title>{t}</title><link>{link}</link>"
        f"<pubDate>Mon, 05 Oct 2026 10:00:00 GMT</pubDate>"
        f"<description><![CDATA[{s}]]></description></item>"
        for t, link, s in items
    )
    return f"<rss version='2.0'><channel><title>x</title>{body}</channel></rss>"


RSS = _rss(
    (
        "Kaynes Semicon Private Limited among PLI approvals - PIB",
        "https://news.google.com/rss/articles/one",
        # A cluster summary: related headlines in a list, none of them companies.
        "<a href='x'>Kaynes Semicon Private Limited among PLI approvals</a>"
        "<ol><li><a href='y'>Govt approves PLI for drone makers</a></li>"
        "<li><a href='z'>Cabinet clears textile incentives</a></li></ol>",
    ),
    (
        "14 applicants provisionally selected under PLI for drones - PIB",
        "https://news.google.com/rss/articles/two",
        "<a href='x'>14 applicants provisionally selected</a>",
    ),
    (
        "Bharat Forge Limited approved under PLI auto scheme - PIB",
        "https://news.google.com/rss/articles/three",
        "",
    ),
)

# A holding the scraper must not report as a competitor.
WATCHLIST = {
    "manufacturing_electronics": [{"ticker": "ACME", "name": "Acme Electronics Ltd"}]
}


def _run(monkeypatch, pages):
    import utils
    from analysis import parsing

    async def fake_fetch(session, url, headers=None, timeout=15):
        answer = pages[url] if url in pages else pages["search"]
        if isinstance(answer, Exception):
            raise answer
        return answer

    async def fake_resolve(name, session):
        return ("KAYNES", "Kaynes") if name.startswith("Kaynes") else (None, None)

    monkeypatch.setattr(utils, "fetch_text_async", fake_fetch)
    monkeypatch.setattr(parsing, "resolve_ticker_from_name_async", fake_resolve)
    return asyncio.run(scraper.scrape_pib_pli_approvals_async(None, WATCHLIST))


def test_a_google_page_falls_back_to_the_headline_and_a_release_is_read(
    monkeypatch, caplog
):
    pages = {
        "search": (200, RSS),
        # Google's own page for the story: not the release.
        "https://news.google.com/rss/articles/one": (200, GOOGLE_PAGE),
        "https://news.google.com/rss/articles/two": (200, PIB_RELEASE),
        "https://news.google.com/rss/articles/three": OSError("connection reset"),
    }
    with caplog.at_level(logging.INFO):
        found = _run(monkeypatch, pages)
    by_name = {c["name"]: c for c in found}
    # From the release's table; the holding is left out.
    assert by_name["Zenith Drone Systems"]["found_in"] == "release page"
    assert "Acme Electronics Ltd" not in by_name
    # From headlines, where the page was Google's or the fetch failed.
    assert by_name["Kaynes Semicon Private Limited"]["found_in"] == "headline"
    assert by_name["Kaynes Semicon Private Limited"]["status"] == "Listed Peer"
    assert by_name["Bharat Forge Limited"]["found_in"] == "headline"
    # Nothing from Google's page, the release's menu, or the related
    # headlines in a summary.
    for junk in (
        "Home",
        "Ministry of Steel",
        "Top stories",
        "For you",
        "Govt approves PLI for drone makers",
        "Cabinet clears textile incentives",
    ):
        assert junk not in by_name
    line = next(
        r.message for r in caplog.records if r.message.startswith("PLI approvals:")
    )
    assert line.startswith("PLI approvals: 3 release(s) in the last 30 days")
    assert "1 link(s) led to a page that was not the release" in line
    assert "1 fetch(es) failed" in line


def test_an_empty_search_says_so(monkeypatch, caplog):
    with caplog.at_level(logging.INFO):
        found = _run(monkeypatch, {"search": (404, "")})
    assert found == []
    line = next(
        r.message for r in caplog.records if r.message.startswith("PLI approvals:")
    )
    assert line.startswith("PLI approvals: search returned HTTP 404")
    assert line.endswith("0 new candidate(s) after removing duplicates and holdings.")


def test_a_pages_menus_are_not_read_as_companies():
    html = """
    <html><body>
      <nav><ul><li>Defence Ministry</li></ul></nav>
      <div id="main-menu"><ul><li>Press Releases</li></ul></div>
      <ul><li><a href="/x">Photo Gallery</a></li></ul>
      <div class="release">
        <ul><li>Optiemus Infracom</li><li>Syrma SGS Technology</li></ul>
      </div>
    </body></html>
    """
    names = [c["name"] for c in _extract_pli_data_from_html(html, "PLI approvals")]
    assert names == ["Optiemus Infracom", "Syrma SGS Technology"]
