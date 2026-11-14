from providers.nse_deals import parse_deal_csv

TRACKED = {"BDL": "Bharat Dynamics Limited", "TCS": "Tata Consultancy Services"}


def test_nse_bulk_deal_parser_requires_tracked_symbol_and_exchange_fields():
    body = (
        "Date,Symbol,Security Name,Client Name,Buy/Sell,Quantity,Wtd. Avg. Price\n"
        "13-Nov-2026,BDL,Bharat Dynamics Limited,ABC Fund,BUY,100000,1025.50\n"
        "13-Nov-2026,UNKNOWN,Unknown Ltd,XYZ Fund,SELL,20000,50\n"
        "13-Nov-2026,TCS,Tata Consultancy Services,,SELL,1000,3000\n"
    )
    rows = parse_deal_csv(body, "Bulk", TRACKED)
    assert len(rows) == 1
    row = rows[0]
    assert row["ticker"] == "BDL"
    assert row["action"] == "Buy"
    assert row["buyer"] == "ABC Fund"
    assert row["seller"] is None
    assert row["quantity"] == 100000
    assert row["value_cr"] == 10.255
    assert row["confidence"] == "exchange_disclosed"
    assert row["source"] == "NSE"


def test_nse_deal_parser_does_not_guess_missing_price_or_action():
    body = (
        "Date,Symbol,Client Name,Buy/Sell,Quantity,Wtd. Avg. Price\n"
        "13-Nov-2026,BDL,ABC Fund,SELL,1000,\n"
        "13-Nov-2026,TCS,XYZ Fund,UNKNOWN,1000,100\n"
    )
    rows = parse_deal_csv(body, "Block", TRACKED)
    assert len(rows) == 1
    assert rows[0]["action"] == "Sell"
    assert rows[0]["seller"] == "ABC Fund"
    assert rows[0]["value_cr"] is None
