"""Institutional activity parser must not invent counterparties or trade direction."""

from scraper import _parse_block_deal_headline


WATCHLIST = [
    ("IIFLCAP", "IIFL Capital Services", "financials"),
    ("TCS", "Tata Consultancy Services", "it_services"),
]


def test_generic_fii_commentary_is_not_a_block_deal():
    headline = (
        "Sensex, Nifty close with rally on FII buying but profit booking "
        "limits gains"
    )
    assert _parse_block_deal_headline(headline, WATCHLIST, headline.lower()) is None


def test_deal_without_a_tracked_company_is_not_attributed():
    headline = (
        "Theleme Partners sells Rs 109 crore worth of unknown company "
        "shares in block deal"
    )
    assert _parse_block_deal_headline(headline, WATCHLIST, headline.lower()) is None


def test_tracked_company_deal_has_explicit_direction_and_ticker():
    headline = (
        "Theleme Partners sells Rs 109 crore worth of IIFL Capital Services "
        "shares in block deal"
    )
    parsed = _parse_block_deal_headline(headline, WATCHLIST, headline.lower())
    assert parsed["ticker"] == "IIFLCAP"
    assert parsed["action"] == "Sell"
    assert parsed["deal_type"] == "Block Deal"
    assert parsed["details"] == "Rs 109 crore"
    assert parsed["buyer"] == "Theleme Partners"
    assert parsed["confidence"] == "headline_attributed"


def test_direction_is_unknown_when_headline_does_not_say_buy_or_sell():
    headline = "Block deal in Tata Consultancy Services shares"
    parsed = _parse_block_deal_headline(headline, WATCHLIST, headline.lower())
    assert parsed["ticker"] == "TCS"
    assert parsed["action"] is None
    assert parsed["buyer"] is None


def test_watchlist_match_without_block_or_bulk_deal_is_ignored():
    headline = "Tata Consultancy Services reports quarterly results"
    assert _parse_block_deal_headline(headline, WATCHLIST, headline.lower()) is None
