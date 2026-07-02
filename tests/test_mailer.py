import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from emails.mailer import build_html_email  # noqa: E402
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
            {"source": "Tech Crunch", "title": "New AI Tool Released"}
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
    assert "badge-positive" in html

    # Stock table checks
    assert "CYB" in html
    assert "Cyber Sec Inc" in html
    assert "₹150.00" in html
    assert "₹200.00" in html
    assert "+33.3%" in html
    assert "Buy (5)" in html
    assert "+20% YoY" in html
    assert "EPS +15%" in html
    assert "New government contract." in html

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
