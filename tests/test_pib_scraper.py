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


# --- PIB's own release text, as a runner fetched it on 19 Oct 2026 ------------
#
# PressReleaseIframePage.aspx?PRID=2314891, cut down: the markup is PIB's, with
# its spans, its images between paragraphs, and the page around the release.

BULK_DRUGS_PAGE = """<html><body><form id="form1">
<div class="leftnav"><ul><li><a href="/m">Ministry of Heavy Industries</a></li>
<li><a href="/f">Ministry of Food Processing Industries</a></li></ul></div>
<table><tr><td>Ministry of Chemicals and Fertilizers : </td></tr><tr><td></td></tr></table>
<div class="container"><div class="innner-page-main-about-us-content-right-part">
<div class="MinistryNameSubhead text-center" id="MinistryName"> Ministry of Chemicals
and Fertilizers : <br/>Department of Pharmaceuticals </div>
<div class="text-center event-heading-background"> <h1 id="Titleh2"> PLI Scheme for
Bulk Drugs for Resilient Pharmaceutical Supply Chain </h1> </div>
<div class="ReleaseDateSubHeaddateTime text-center pt20" id="PrDateTime"> Posted On:
25 SEP 2026 4:36PM by PIB Delhi </div>
<p><span><span><strong>The Production Linked Incentive (PLI) Scheme </strong>for
<strong>Bulk Drugs</strong> is strengthening India’s domestic capabilities in
manufacturing critical Key Starting Materials (KSMs), Drug Intermediates (DIs) and
Active Pharmaceutical Ingredients (APIs).</span></span></p>
<p><span><span><strong>Lyfius Pharma Pvt. Ltd., a subsidiary of Aurobindo Pharma
Limited</strong>, has established a large-scale <strong>Penicillin G</strong>
manufacturing facility at Kakinada SEZ in Andhra Pradesh.</span></span></p>
<p><span><span><strong><img/><img/></strong></span></span></p>
<p><span><span><strong>Kinvan Private Limited</strong>, a DPB Group company, has
established a <strong>400 MT per annum</strong> facility at Nalagarh, Himachal
Pradesh.</span></span></p>
<p><span><span><strong>Andhra Organics Limited (AOL)</strong>, a wholly owned
subsidiary of Virchow Laboratories Limited, has commissioned manufacturing
facilities at Pydibhimavaram in Srikakulam district of Andhra Pradesh.The projects
involve a combined investment of <strong>₹151.47 crore</strong>.</span></span></p>
<p><span><span><strong>Meghmani LLP</strong> has established a <strong>13,500 MT per
annum</strong> facility for <strong>Para Amino Phenol (PAP)</strong> at Dahej,
Gujarat.</span></span></p>
<p><span><span><strong>Centrient Pharmaceuticals India Private Limited</strong> has
established a greenfield <strong>Atorvastatin API</strong> facility in Nawanshahr,
Punjab.</span></span></p>
<p><span><span>*****</span></span></p> <p><span><span><strong>PC/PM</strong></span></span></p>
<span id="ReleaseId">(Release ID: 2314891)</span> <span id="lblViews">Visitor Counter :
1176</span> <div class="ReleaseLang">Read this release in: <a> Urdu </a> ,
<a> हिन्दी </a> </div> <div class="RelTag"> <ul> </ul> </div>
</div></div></form></body></html>"""

# PRID=2314746: one release about three schemes, each in its own section.
SCHEMES_PAGE = """<html><body><div class="innner-page-main-about-us-content-right-part">
<h1 id="Titleh2"> Production Linked Incentive Schemes have Strengthened India’s
Pharmaceutical, Bulk Drugs and Medical Devices Manufacturing Ecosystem </h1>
<div id="PrDateTime"> Posted On: 25 SEP 2026 12:46PM by PIB Delhi </div>
<h3><span><strong><span>a) </span></strong><strong><span>PLI Scheme for Bulk Drugs :
Strengthening Self-Reliance in Critical APIs</span></strong></span></h3>
<h3><span><span>The commissioning of new manufacturing units is strengthening the
domestic ecosystem for critical pharmaceutical raw materials. Companies such as
Lyfius Pharma, Kinvan Private Limited, Andhra Organics Limited (AOL), Meghmani LLP,
Centrient Pharmaceuticals India Pvt. Ltd have contributed to strengthening of
domestic manufacturing of critical APIs.</span></span></h3>
<h3><span><strong><span>b) </span></strong><strong><span>PLI Scheme for
Pharmaceuticals : Driving High-Value Pharmaceutical Manufacturing</span></strong>
</span></h3>
<p><span><span>Companies such as Sun Pharmaceutical Industries Limited,
AurobindoPharma Limited, Dr. Reddy’s Laboratories Limited, Lupin Limited, Cipla
Limited, Intas Pharmaceuticals Limited, Torrent Pharmaceuticals Limited have
expanded their capacities to manufacture complex generics.</span></span></p>
<h3><span><strong><span>c) </span></strong><strong><span>PLI Scheme for Medical
Devices: Advancing Indigenous Manufacturing</span></strong></span></h3>
<h3><span><span>Companies such as <strong>GE Healthcare, Siemens, Philips, Varex,
Nipro and Omron</strong> have established or expanded manufacturing operations in
the country.</span></span></h3>
</div></body></html>"""


def _release(html):
    from providers import pib

    release = pib.read_release(html)
    return _extract_pli_data_from_html(release["html"], release["title"], "x")


def test_a_release_is_read_from_its_own_text_and_its_names_kept_whole():
    from providers import pib

    release = pib.read_release(BULK_DRUGS_PAGE)
    assert release["title"].startswith("PLI Scheme for Bulk Drugs")
    assert release["date"] == "2026-09-25"
    companies = _extract_pli_data_from_html(
        release["html"], release["title"], release["date"]
    )
    assert [c["name"] for c in companies] == [
        "Lyfius Pharma Pvt. Ltd.",
        "Aurobindo Pharma Limited",
        "Kinvan Private Limited",
        "Andhra Organics Limited",
        "Virchow Laboratories Limited",
        "Meghmani LLP",
        "Centrient Pharmaceuticals India Private Limited",
    ]
    # "PLI Scheme for Bulk Drugs", not the "Pharmaceutical" later in the title.
    assert {c["sector"] for c in companies} == {"Bulk Drugs"}
    assert {c["date"] for c in companies} == {"2026-09-25"}


def test_a_page_without_a_releases_text_is_not_read():
    from providers import pib

    assert pib.read_release("<html><body><ul><li>Home</li></ul></body></html>") is None


def test_a_release_about_several_schemes_files_each_name_under_its_own():
    companies = {c["name"]: c["sector"] for c in _release(SCHEMES_PAGE)}
    assert companies == {
        "Lyfius Pharma": "Bulk Drugs",
        "Kinvan Private Limited": "Bulk Drugs",
        "Andhra Organics Limited": "Bulk Drugs",
        "Meghmani LLP": "Bulk Drugs",
        "Centrient Pharmaceuticals India Pvt. Ltd": "Bulk Drugs",
        "Sun Pharmaceutical Industries Limited": "Pharmaceuticals",
        "AurobindoPharma Limited": "Pharmaceuticals",
        "Dr. Reddy’s Laboratories Limited": "Pharmaceuticals",
        "Lupin Limited": "Pharmaceuticals",
        "Cipla Limited": "Pharmaceuticals",
        "Intas Pharmaceuticals Limited": "Pharmaceuticals",
        "Torrent Pharmaceuticals Limited": "Pharmaceuticals",
        "GE Healthcare": "Medical Devices",
        "Siemens": "Medical Devices",
        "Philips": "Medical Devices",
        "Varex": "Medical Devices",
        "Nipro": "Medical Devices",
        "Omron": "Medical Devices",
    }


def test_government_words_and_cut_names_are_not_companies():
    html = """<div>
      <p>The Ministry of Heavy Industries and the Ministry of Food Processing
      Industries said the PLI Scheme for White Goods is open. Applicants may
      register as a Private Limited company.</p>
      <p>The plant was set up by Aurobindo. Kinvan Private Limited has started
      supplies, and Lupin Limited and Cipla Limited have expanded.</p>
    </div>"""
    names = [c["name"] for c in _extract_pli_data_from_html(html, "PLI approvals")]
    assert names == ["Kinvan Private Limited", "Lupin Limited", "Cipla Limited"]


def test_names_are_found_whatever_their_spelling():
    html = (
        "<p>Beneficiaries include M/s Dixon Technologies (India) Limited, "
        "ideaForge Technology Limited, KINVAN PRIVATE LIMITED and "
        "Amber Enterprises India Ltd. The rest follow.</p>"
    )
    names = [c["name"] for c in _extract_pli_data_from_html(html, "PLI approvals")]
    assert names == [
        "Dixon Technologies (India) Limited",
        "ideaForge Technology Limited",
        "KINVAN PRIVATE LIMITED",
        "Amber Enterprises India Ltd.",
    ]


def test_each_scheme_carries_the_sectors_that_compete_under_it():
    by_name = {
        c["name"]: c
        for c in _extract_pli_data_from_html(
            "<p>Selected: Blue Star Climatech Limited.</p>",
            "PLI Scheme for White Goods: applicants selected",
        )
    }
    assert by_name["Blue Star Climatech Limited"]["sector"] == "White Goods"
    assert by_name["Blue Star Climatech Limited"]["scheme_sectors"] == [
        "manufacturing_electronics"
    ]
    unknown = _extract_pli_data_from_html("<p>Acme Limited.</p>", "PLI approvals")
    assert unknown[0]["scheme_sectors"] is None


def test_a_pages_menus_are_not_read_as_companies():
    html = """
    <html><body>
      <nav><ul><li>Defence Ministry</li></ul></nav>
      <div id="main-menu"><ul><li>Press Releases</li></ul></div>
      <ul><li><a href="/x">Photo Gallery</a></li></ul>
      <div class="release">
        <p>The applicants selected are:</p>
        <ul><li>Optiemus Infracom</li><li>Syrma SGS Technology</li></ul>
      </div>
    </body></html>
    """
    names = [c["name"] for c in _extract_pli_data_from_html(html, "PLI approvals")]
    assert names == ["Optiemus Infracom", "Syrma SGS Technology"]


def test_a_list_of_unsuffixed_capitalised_items_is_not_a_list_of_names():
    html = "<ul><li>Bulk Drugs</li><li>Medical Devices</li><li>Press Releases</li></ul>"
    assert _extract_pli_data_from_html(html, "PLI approvals") == []


def test_a_table_is_read_only_down_its_name_column():
    html = """<table>
      <tr><th>S. No.</th><th>Name of the Applicant</th><th>Investment (₹ crore)</th></tr>
      <tr><td>1</td><td>M/s Zenith Cooling Systems</td><td>120</td></tr>
      <tr><td>2</td><td>Amber Enterprises India Limited</td><td>500</td></tr>
      <tr><td></td><td>Total</td><td>620</td></tr>
    </table>
    <table><tr><td>Ministry of Commerce and Industry :</td></tr></table>"""
    names = [c["name"] for c in _extract_pli_data_from_html(html, "PLI approvals")]
    assert names == ["Zenith Cooling Systems", "Amber Enterprises India Limited"]


# --- PIB's list of a day's releases -------------------------------------------

import datetime  # noqa: E402

from providers import pib  # noqa: E402

TODAY = datetime.date(2026, 10, 19)


def _list_page(day, releases):
    """PIB's allRel.aspx as it answers, cut down to what is read from it."""

    def menu(name, value, values):
        options = "".join(
            f"<option value='{v}'{' selected' if v == value else ''}>{v}</option>"
            for v in values
        )
        return f"<select name='{name}'>{options}</select>"

    links = "".join(
        f"<li><a href='/PressReleaseDetail.aspx?PRID={prid}'>{title}</a></li>"
        for title, prid in releases
    )
    return (
        "<html><body><form method='post' action='./allRel.aspx?reg=3&amp;lang=1'>"
        "<input type='hidden' name='__EVENTTARGET' value=''/>"
        "<input type='hidden' name='__VIEWSTATE' value='VS'/>"
        "<input type='hidden' name='__EVENTVALIDATION' value='EV'/>"
        "<input type='image' name='ctl00$ContentPlaceHolder1$Print1$print'/>"
        + menu("ctl00$Bar1$ddlLang", "1", ["2", "1", "3"])
        + menu("ctl00$ContentPlaceHolder1$ddlday", str(day.day), [str(d) for d in range(32)])
        + menu("ctl00$ContentPlaceHolder1$ddlMonth", str(day.month), [str(m) for m in range(1, 13)])
        + menu("ctl00$ContentPlaceHolder1$ddlYear", str(day.year), ["2026", "2025"])
        + f"<ul>{links}</ul></form></body></html>"
    )  # fmt: skip


def test_the_form_is_posted_back_as_a_browser_would():
    fields = pib.form_fields(_list_page(TODAY, []))
    assert fields["__VIEWSTATE"] == "VS"
    assert fields["ctl00$Bar1$ddlLang"] == "1"
    assert fields["ctl00$ContentPlaceHolder1$ddlday"] == "19"
    assert "ctl00$ContentPlaceHolder1$Print1$print" not in fields
    assert pib.shown_day(fields) == TODAY


def test_release_links_carry_the_prid_once_each():
    page = _list_page(
        TODAY, [("PLI for drones", "2325001"), ("PLI for drones", "2325001")]
    )
    assert pib.release_links(page) == [
        (
            "PLI for drones",
            "2325001",
            "https://www.pib.gov.in/PressReleaseDetail.aspx?PRID=2325001",
        )
    ]


def test_a_google_headline_is_matched_to_pibs_title():
    pib_title = (
        "Production Linked Incentive Schemes have Strengthened India’s "
        "Pharmaceutical, Bulk Drugs and Medical Devices Manufacturing Ecosystem"
    )
    assert pib.same_title(f"{pib_title} - Press Information Bureau", pib_title)
    assert pib.same_title(pib_title.replace("’", "'") + " - www.pib.gov.in", pib_title)
    # Cut short, as a list can show it.
    assert pib.same_title(pib_title, pib_title[:80])
    # A short title must match whole: "PLI Scheme for" begins many.
    assert not pib.same_title(
        "PLI Scheme for Drones", "PLI Scheme for Drones and Parts"
    )
    assert not pib.same_title("Untitled - Press Information Bureau", pib_title)


def test_a_story_is_looked_for_under_indias_date():
    # 19:30 GMT on 5 Oct is 01:00 on 6 Oct in Delhi.
    assert pib.ist_day("Mon, 05 Oct 2026 19:30:00 GMT") == datetime.date(2026, 10, 6)
    assert pib.ist_day("Mon, 05 Oct 2026 10:00:00 GMT") == datetime.date(2026, 10, 5)
    assert pib.ist_day("not a date") is None


# --- the scraper end to end, with no network ---------------------------------

import asyncio  # noqa: E402
import logging  # noqa: E402
import urllib.parse  # noqa: E402

import scraper  # noqa: E402


def _rss(*items):
    body = "".join(
        f"<item><title>{t}</title><link>{link}</link>"
        f"<pubDate>{when}</pubDate>"
        f"<description><![CDATA[{s}]]></description></item>"
        for t, link, when, s in items
    )
    return f"<rss version='2.0'><channel><title>x</title>{body}</channel></rss>"


WHITE_GOODS = "PLI Scheme for White Goods: 24 applicants selected in the fourth round"
TEXTILES = "PLI Scheme for Textiles: 10 more applicants approved"
PHARMA = "PLI Scheme for Pharmaceuticals: beneficiaries expand capacity"
KAYNES = "Kaynes Semicon Private Limited among PLI approvals"

RSS = _rss(
    (
        f"{WHITE_GOODS} - Press Information Bureau",
        "https://news.google.com/rss/articles/one",
        # Late on 5 Oct in GMT: 6 Oct in India, and PIB posted it on the 5th.
        "Mon, 05 Oct 2026 19:30:00 GMT",
        "",
    ),
    (
        f"{PHARMA} - PIB",
        "https://news.google.com/rss/articles/two",
        "Wed, 07 Oct 2026 08:00:00 GMT",
        "",
    ),
    (
        f"{KAYNES} - PIB",
        "https://news.google.com/rss/articles/three",
        "Thu, 08 Oct 2026 06:00:00 GMT",
        # A cluster summary: related headlines in a list, none of them companies.
        "<a href='x'>Kaynes Semicon Private Limited among PLI approvals</a>"
        "<ol><li><a href='y'>Govt approves PLI for drone makers</a></li></ol>",
    ),
)

# What each day's list holds.
DAYS = {
    TODAY: [("Prime Minister greets citizens", "2325041")],
    datetime.date(2026, 10, 8): [("Cabinet approves a rail line", "2320001")],
    datetime.date(2026, 10, 7): [
        (PHARMA, "2319001"),
        ("Prime Minister greets citizens", "2319002"),
    ],
    datetime.date(2026, 10, 6): [("Cabinet approves a rail line", "2318001")],
    datetime.date(2026, 10, 5): [
        (WHITE_GOODS, "2317001"),
        (TEXTILES, "2317002"),
        ("Cabinet approves a rail line", "2317003"),
    ],
}


def _release_page(title, day, body):
    return (
        "<html><body><div class='leftnav'><ul>"
        "<li><a href='/m'>Ministry of Heavy Industries</a></li></ul>"
        "<p>Other releases: Bharat Heavy Electricals Limited signs MoU</p></div>"
        "<div class='innner-page-main-about-us-content-right-part'>"
        f"<h1 id='Titleh2'>{title}</h1>"
        f"<div id='PrDateTime'>Posted On: {day} 5:00PM by PIB Delhi</div>"
        f"{body}</div></body></html>"
    )


RELEASES = {
    "2317001": _release_page(
        WHITE_GOODS,
        "05 OCT 2026",
        "<table><tr><th>S. No.</th><th>Name of the Applicant</th></tr>"
        "<tr><td>1</td><td>M/s Amber Enterprises India Limited</td></tr>"
        "<tr><td>2</td><td>Acme Electronics Ltd</td></tr>"
        "<tr><td>3</td><td>Zenith Cooling Systems</td></tr></table>",
    ),
    "2317002": _release_page(
        TEXTILES,
        "05 OCT 2026",
        "<p>Welspun Living Limited and Zeta Fabrics Private Limited are among "
        "those approved.</p>",
    ),
    "2319001": _release_page(
        PHARMA,
        "07 OCT 2026",
        "<p>Companies such as Lupin Limited and Cipla Limited have expanded.</p>",
    ),
}

WATCHLIST = {
    "manufacturing_electronics": [{"ticker": "ACME", "name": "Acme Electronics"}],
    "textiles_apparel": [{"ticker": "WELSPUNLIV", "name": "Welspun Living"}],
}
REGISTERED = {
    "AMBER": "Amber Enterprises India Limited",
    "ACME": "Acme Electronics Limited",
}


def _run(monkeypatch, search=(200, RSS), list_status=200):
    import utils
    from analysis import parsing

    asked = {"get": [], "post": [], "resolved": []}

    async def fake_fetch(session, url, headers=None, timeout=15):
        asked["get"].append(url)
        if url == pib.LIST_URL:
            return list_status, _list_page(TODAY, DAYS[TODAY])
        query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        if "PRID" in query:
            prid = query["PRID"][0]
            return (200, RELEASES[prid]) if prid in RELEASES else (404, "")
        return search

    async def fake_post(session, url, data, headers=None, timeout=30):
        asked["post"].append(data)
        day = datetime.date(
            int(data["ctl00$ContentPlaceHolder1$ddlYear"]),
            int(data["ctl00$ContentPlaceHolder1$ddlMonth"]),
            int(data["ctl00$ContentPlaceHolder1$ddlday"]),
        )
        return 200, _list_page(day, DAYS.get(day, []))

    async def fake_resolve(name, session):
        asked["resolved"].append(name)
        return ("KAYNES", "Kaynes") if name.startswith("Kaynes") else (None, None)

    monkeypatch.setattr(utils, "fetch_text_async", fake_fetch)
    monkeypatch.setattr(utils, "post_form_async", fake_post)
    monkeypatch.setattr(parsing, "resolve_ticker_from_name_async", fake_resolve)
    found = asyncio.run(
        scraper.scrape_pib_pli_approvals_async(None, WATCHLIST, registered=REGISTERED)
    )
    return found, asked


def _line(caplog):
    return next(
        r.message for r in caplog.records if r.message.startswith("PLI approvals:")
    )


def test_releases_are_found_on_pibs_own_list_and_read_from_pib(monkeypatch, caplog):
    with caplog.at_level(logging.INFO):
        found, asked = _run(monkeypatch)
    by_name = {c["name"]: c for c in found}
    assert sorted(by_name) == [
        "Amber Enterprises India Limited",
        "Kaynes Semicon Private Limited",
        "Zenith Cooling Systems",
        "Zeta Fabrics Private Limited",
    ]
    amber = by_name["Amber Enterprises India Limited"]
    assert amber["found_in"] == "release page"
    assert amber["sector"] == "White Goods"
    assert amber["watch_sectors"] == ["manufacturing_electronics"]
    assert amber["date"] == "2026-10-05"
    assert amber["announcement"] == WHITE_GOODS
    assert (
        amber["link"] == "https://www.pib.gov.in/PressReleaseDetail.aspx?PRID=2317001"
    )
    # NSE's registered name settles the ticker; Yahoo is not asked.
    assert (amber["ticker"], amber["status"]) == ("AMBER", "Listed Peer")
    assert "Amber Enterprises India Limited" not in asked["resolved"]
    assert by_name["Zenith Cooling Systems"]["status"] == "Unlisted"
    # The same day's other PLI release, which Google did not carry.
    assert by_name["Zeta Fabrics Private Limited"]["sector"] == "Textiles"
    # Not on PIB's lists: read from its headline.
    assert by_name["Kaynes Semicon Private Limited"]["found_in"] == "headline"
    assert by_name["Kaynes Semicon Private Limited"]["status"] == "Listed Peer"
    # PIB's lists were asked for by day: today's came with the page; each
    # other day was the form posted back with that day.
    posted = [
        (d["ctl00$ContentPlaceHolder1$ddlday"], d["__EVENTTARGET"], d["__VIEWSTATE"])
        for d in asked["post"]
    ]
    assert posted == [
        ("8", "ctl00$ContentPlaceHolder1$ddlday", "VS"),
        ("7", "ctl00$ContentPlaceHolder1$ddlday", "VS"),
        ("6", "ctl00$ContentPlaceHolder1$ddlday", "VS"),
        ("5", "ctl00$ContentPlaceHolder1$ddlday", "VS"),
    ]
    assert asked["get"].count(pib.LIST_URL) == 1
    line = _line(caplog)
    assert line.startswith(
        "PLI approvals: 3 search result(s) in the last 30 days, 3 release(s); "
        "2 found on PIB's lists of releases (5 day list(s) read), "
        "1 more PLI release(s) on those days; 3 release(s) read from PIB"
    )
    assert "left out under schemes no holding works in: Pharmaceuticals 2" in line
    assert line.endswith("4 new candidate(s) after removing duplicates and holdings.")


def test_holdings_menus_and_other_schemes_are_left_out(monkeypatch):
    found, _ = _run(monkeypatch)
    names = {c["name"] for c in found}
    # Holdings: by name, and by NSE's registered name.
    assert "Acme Electronics Ltd" not in names
    assert "Welspun Living Limited" not in names
    # Under a scheme no holding works in.
    assert not names & {"Lupin Limited", "Cipla Limited"}
    # The page around the release, and a cluster summary's other headlines.
    for junk in (
        "Ministry of Heavy Industries",
        "Heavy Industries",
        "Bharat Heavy Electricals Limited",
        "Govt approves PLI for drone makers",
    ):
        assert junk not in names


def test_pib_refusing_its_list_is_reported_and_asked_once(monkeypatch, caplog):
    with caplog.at_level(logging.INFO):
        found, asked = _run(monkeypatch, list_status=403)
    assert asked["get"].count(pib.LIST_URL) == 1
    assert asked["post"] == []
    # Every story falls back to its headline.
    assert [c["name"] for c in found] == ["Kaynes Semicon Private Limited"]
    line = _line(caplog)
    assert "0 found on PIB's lists of releases (0 day list(s) read)" in line
    assert "the list of releases returned HTTP 403" in line


def test_a_list_that_will_not_change_day_stops_the_asking(monkeypatch):
    import utils

    async def fake_fetch(session, url, headers=None, timeout=15):
        return 200, _list_page(TODAY, [])

    async def fake_post(session, url, data, headers=None, timeout=30):
        return 200, _list_page(TODAY, [])

    monkeypatch.setattr(utils, "fetch_text_async", fake_fetch)
    monkeypatch.setattr(utils, "post_form_async", fake_post)
    index = pib.DayIndex(None)
    day = datetime.date(2026, 10, 5)
    assert asyncio.run(index.releases_on(day)) == []
    assert "would not show 2026-10-05" in index.failed
    assert asyncio.run(index.releases_on(datetime.date(2026, 10, 4))) is None


def test_an_empty_search_says_so(monkeypatch, caplog):
    with caplog.at_level(logging.INFO):
        found, asked = _run(monkeypatch, search=(404, ""))
    assert found == []
    assert asked["post"] == []
    line = _line(caplog)
    assert line.startswith("PLI approvals: search returned HTTP 404")
    assert line.endswith("0 new candidate(s) after removing duplicates and holdings.")
