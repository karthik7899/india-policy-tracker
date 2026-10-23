import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from emails.mailer import build_html_email  # noqa: E402
from emails import mailer  # noqa: E402
from config import SECTOR_METADATA  # noqa: E402
import datetime  # noqa: E402


def test_build_html_email_success():
    """Test building HTML email with fully populated valid data."""
    brief_data = {
        "cybersecurity": [
            {
                "impact": "Positive",
                "link": "http://example.com/cyber",
                "title": "New Cyber Law",
                "source": "PIB",
                "date": "2026-03-01",
            }
        ],
        "corporate_agreements": [
            {"source": "Business Today", "title": "Tech Corp Acquires Startup"}
        ],
        "product_launches": [
            {
                "source": "Tech Crunch",
                "company": "Cyber Sec Inc",
                "title": "New AI Tool Released",
            }
        ],
        "margin_of_safety": [
            {
                "ticker": "DEF",
                "name": "Defensive Corp",
                "price": "50",
                "is_defensive_pass": True,
                "is_bargain": False,
            }
        ],
        "buffett_valuation": [
            {
                "ticker": "MOAT",
                "moat_status": "Wide",
                "owner_earnings": 100,
                "passed_retained_test": True,
            }
        ],
        "emerging_players": {
            "cybersecurity": [
                {"name": "New Cyber Startup", "ticker": "NCS", "status": "Scanned"},
                "Unknown Player",
            ]
        },
    }

    watchlist = {
        "cybersecurity": [
            {
                "ticker": "CYB",
                "name": "Cyber Sec Inc",
                "price": "150.00",
                "target": "200.00",
                "growth_pct": "+33.3%",
                "rating": "Buy",
                "analyst_count": 5,
                "revenue_growth": "+20%",
                "earnings_growth": "+15%",
                "catalyst": "New government contract.",
                "screener": {"valuation_alerts": ["High P/E"]},
            }
        ]
    }

    html = build_html_email(brief_data, watchlist)

    today_str = datetime.date.today().strftime("%B %d, %Y")

    # Header check
    assert "India Policy &amp; Growth Sector Brief" in html
    assert today_str in html

    # News checks
    assert "New Cyber Law" in html
    # "Positive Impact" is no longer badged: the keyword scorer marked nearly
    # every item positive, so the badge carried no information.
    assert "Positive Impact" not in html

    # Stock table checks
    assert "CYB" in html
    assert "Cyber Sec Inc" in html
    assert "₹150.00" in html
    assert "₹200.00" in html
    assert "+33.3%" in html
    assert "Buy (5)" in html
    assert "+20% YoY" in html
    assert "EPS +15%" in html
    # The fixed config description is not repeated in the daily email: it is
    # identical every morning and lives on the dashboard.
    assert "New government contract." not in html

    # Emerging players check
    assert "Emerging Competitor Radar" in html
    assert "New Cyber Startup" in html

    # Special sections checks
    assert "Corporate Agreements &amp; Partnerships" in html
    assert "Tech Corp Acquires Startup" in html

    assert "Product Launches &amp; Innovations" in html
    assert "New AI Tool Released" in html

    # Valuation Checks
    assert "Graham Margin of Safety Pass List" in html
    assert "Defensive Corp" in html

    assert "Warren Buffett Allocation &amp; Moat Screens" in html
    assert "MOAT" in html
    assert "Wide" in html

    assert "Valuation Caution List &amp; Warnings" in html
    assert "High P/E" in html


def test_caution_list_keeps_the_order_the_screens_ran():
    """Repeats are dropped and the rest keep their order. The list used to go
    through a set, whose order follows each run's hash seed, so one holding's
    alerts came out in a different order every morning."""
    alerts = [
        "Fails Current Ratio (< 2.0)",
        "Fails Debt Limit (Debt > Net Assets)",
        "Fails P/E Screen (P/E 34.0 > 15 & Price > Intrinsic)",
        "No Dividend Yield",
        "Hyper-Growth Reality Check (P/E > 30 & revenue growth decelerating)",
        "Fails Debt Limit (Debt > Net Assets)",
    ]
    brief_data = {
        "margin_of_safety": [
            {"ticker": "DEF", "name": "Defensive Corp", "price": "50"},
        ]
    }
    watchlist = {
        "cybersecurity": [
            {
                "ticker": "CYB",
                "name": "Cyber Sec Inc",
                "price": "150.00",
                "screener": {"valuation_alerts": alerts},
            }
        ]
    }

    html = build_html_email(brief_data, watchlist)

    assert (
        "Fails Current Ratio (&lt; 2.0), Fails Debt Limit (Debt &gt; Net Assets), "
        "Fails P/E Screen (P/E 34.0 &gt; 15 &amp; Price &gt; Intrinsic), "
        "No Dividend Yield, "
        "Hyper-Growth Reality Check (P/E &gt; 30 &amp; revenue growth decelerating)"
        "</td>"
    ) in html


def test_build_html_email_empty():
    """Test building HTML email with empty dictionaries."""
    brief_data = {}
    watchlist = {}

    html = build_html_email(brief_data, watchlist)

    today_str = datetime.date.today().strftime("%B %d, %Y")

    # Ensure headers and footers are still there
    assert "India Policy &amp; Growth Sector Brief" in html
    assert today_str in html
    assert "Policy Tracker Archive Dashboard" in html

    # Ensure none of the optional sections broke or appear unexpectedly
    assert "Corporate Agreements &amp; Partnerships" not in html
    assert "Product Launches &amp; Innovations" not in html
    assert "Institutional Capital &amp; Fund Flow Tracker" not in html
    assert "Core Value Investing Matrix" not in html


# ---------------------------------------------------------------------------
# size ladder
# ---------------------------------------------------------------------------


def _bulky_brief():
    """A briefing large enough to exceed any sane budget."""
    news = [
        {
            "title": f"A fairly long sector headline number {i} about policy",
            "link": "https://example.com/x",
            "date": "Mon, 27 Jul 2026 06:00:00 GMT",
            "source": "Example Wire",
            "impact": "Positive",
        }
        for i in range(8)
    ]
    return {sector: list(news) for sector in list(SECTOR_METADATA)[:6]}


def _bulky_watchlist():
    stock = {
        "ticker": "AAA",
        "name": "Alpha Industries",
        "price": "100.00",
        "target": "150.00",
        "growth_pct": "+50.0%",
        "catalyst": "A reasonably wordy catalyst describing the thesis at length.",
        "screener": {"pe_ratio": 20.0, "roce": 18.0, "market_cap": 5000.0},
    }
    return {
        sector: [dict(stock, ticker=f"T{i}") for i in range(5)]
        for sector in list(SECTOR_METADATA)[:6]
    }


def test_ladder_steps_down_until_it_fits(monkeypatch):
    """Two rungs used to mean a breaching compact render shipped clipped."""
    brief, wl = _bulky_brief(), _bulky_watchlist()
    full = len(mailer._render_email(brief, wl, mailer._CAPS_NORMAL).encode())
    minimal = len(mailer._render_email(brief, wl, mailer._CAPS_MINIMAL).encode())
    assert minimal < full, "the floor must actually be smaller"

    # A budget only the floor can meet.
    monkeypatch.setattr(mailer, "_SIZE_BUDGET_BYTES", minimal + 10)
    assert len(mailer.build_html_email(brief, wl).encode()) == minimal


def test_generous_budget_keeps_full_richness(monkeypatch):
    brief, wl = _bulky_brief(), _bulky_watchlist()
    monkeypatch.setattr(mailer, "_SIZE_BUDGET_BYTES", 10_000_000)
    full = len(mailer._render_email(brief, wl, mailer._CAPS_NORMAL).encode())
    assert len(mailer.build_html_email(brief, wl).encode()) == full


def test_unmeetable_budget_ships_the_floor_rather_than_nothing(monkeypatch, caplog):
    """A clipped briefing must not look like a delivered one."""
    import logging

    brief, wl = _bulky_brief(), _bulky_watchlist()
    monkeypatch.setattr(mailer, "_SIZE_BUDGET_BYTES", 100)
    with caplog.at_level(logging.ERROR):
        html = mailer.build_html_email(brief, wl)
    assert html, "must still return a renderable email"
    assert any("tightest caps" in r.message for r in caplog.records)


def test_ladder_is_monotonically_smaller():
    brief, wl = _bulky_brief(), _bulky_watchlist()
    sizes = [
        len(mailer._render_email(brief, wl, caps).encode())
        for _, caps in mailer._CAP_LADDER
    ]
    assert sizes == sorted(sizes, reverse=True), sizes


def test_a_small_overrun_costs_a_small_trim(monkeypatch):
    """A full render that only just misses the budget keeps nearly all of it,
    rather than falling to compact and losing ~16 KB for a 1 KB overrun."""
    brief, wl = _bulky_brief(), _bulky_watchlist()
    full = len(mailer._render_email(brief, wl, mailer._CAPS_NORMAL).encode())
    trimmed = len(mailer._render_email(brief, wl, mailer._CAPS_TRIMMED).encode())
    assert trimmed < full
    monkeypatch.setattr(mailer, "_SIZE_BUDGET_BYTES", full - 1)
    assert len(mailer.build_html_email(brief, wl).encode()) == trimmed


# ---------------------------------------------------------------------------
# Inline styles hoisted into classes
# ---------------------------------------------------------------------------


def _page(body, css=".a { color: red; }"):
    return (
        f"<!DOCTYPE html><html><head><style>{css}</style></head><body>"
        f'<span class="preheader">p</span><div class="container">{body}</div>'
        "</body></html>"
    )


def test_repeated_inline_styles_move_into_classes():
    common = "color: #94a3b8; font-size: 11px;"
    html = _page(
        f"<p style='{common}'>a</p>" * 3
        + f"<span class='kpi' style='{common}'>b</span>"
        + "<b style='color: blue'>once</b>"
        + "<i style='color: #34d399 !important;'>i</i>" * 4
    )
    out = mailer._hoist_inline_styles(html)
    assert ".container .s0{color:#94a3b8;font-size:11px}" in out
    assert out.count('<p class="s0">') == 3
    # An element's own class keeps its place, with the hoisted one after it.
    assert "<span class='kpi s0'>" in out
    # Used once, it saves nothing; with !important, a class could not
    # outrank what the inline style does.
    assert "<b style='color: blue'>" in out
    assert out.count("style='color: #34d399 !important;'") == 4
    # The stylesheet is minified on the way.
    assert "<style>.a{color:red}.container .s0{" in out


def _element_styles(html):
    """Per element: tag, classes other than hoisted ones, its declarations
    (a hoisted class read back from its rule) and its other attributes."""
    import re

    rules = dict(re.findall(r"\.container \.(s\d+)\{([^}]*)\}", html))
    out = []
    for match in mailer._TAG_RE.finditer(html[html.find('<div class="container">') :]):
        attrs = {
            a.group(1).lower(): (a.group(2) or "")[1:-1]
            for a in mailer._ATTR_RE.finditer(match.group(2))
        }
        classes = attrs.get("class", "").split()
        hoisted = [c for c in classes if c in rules]
        style = attrs.get("style")
        if hoisted:
            declared = rules[hoisted[0]]
        elif style is not None:
            declared = mailer._declarations(style) or style
        else:
            declared = None
        out.append(
            (
                match.group(1).lower(),
                [c for c in classes if c not in rules],
                declared,
                sorted((k, v) for k, v in attrs.items() if k not in ("class", "style")),
            )
        )
    return out


def test_a_hoisted_email_keeps_every_elements_style(monkeypatch):
    """Read back, every element carries exactly the declarations it was
    rendered with. (The cascade was checked in Chromium on 15-22 Oct 2026's
    emails: every computed property and box identical at 1024 and 375 px.)"""
    brief, wl = _bulky_brief(), _bulky_watchlist()
    hoisted = mailer._render_email(brief, wl, mailer._CAPS_NORMAL)
    monkeypatch.setattr(mailer, "_hoist_inline_styles", lambda html: html)
    plain = mailer._render_email(brief, wl, mailer._CAPS_NORMAL)

    assert ".container .s0{" in hoisted
    assert len(hoisted.encode()) < len(plain.encode())
    assert _element_styles(hoisted) == _element_styles(plain)


def test_the_stylesheet_stays_under_gmails_limit(monkeypatch):
    import re

    brief, wl = _bulky_brief(), _bulky_watchlist()
    html = mailer._render_email(brief, wl, mailer._CAPS_NORMAL)
    css = re.search(r"<style>(.*?)</style>", html, re.S).group(1)
    assert len(css) <= mailer._STYLE_BUDGET_BYTES

    # With no room left, nothing is hoisted and every style stays inline.
    monkeypatch.setattr(mailer, "_STYLE_BUDGET_BYTES", 0)
    html = mailer._render_email(brief, wl, mailer._CAPS_NORMAL)
    assert ".container .s0" not in html and "style=" in html
