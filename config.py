# config.py
import os
import json
from logger import log

STOCK_WATCHLIST = {
    "aerospace_defence": [
        {
            "analyst_count": 24,
            "catalyst": "State aerospace major, expanding "
            "local fighter jet assembly and "
            "benefiting from custom duty "
            "exemptions.",
            "earnings_growth": "+5.5%",
            "growth_pct": "+26.4%",
            "name": "Hindustan Aeronautics",
            "price": "4192.30",
            "rating": "Buy",
            "rec_score": 1.8,
            "revenue_growth": "+1.8%",
            "screener": {
                "book_value": "614",
                "capex": 2788.4,
                "current_ratio": 1.31,
                "dividend_yield": "0.95",
                "graham_intrinsic_value": 14681.2,
                "hyper_growth_warning": False,
                "is_bargain": False,
                "latest_quarter": "Mar 2026",
                "market_cap": "280371",
                "moat_status": "Strong (Wide " "Moat)",
                "ncav_per_share": 426.6,
                "net_current_assets": 28532.0,
                "owner_earnings": 13996.5,
                "pe_ratio": "30.8",
                "q_eps": "62.74",
                "q_net_profit": "4196",
                "q_sales": "13942",
                "qoq_profit_growth": 124.7,
                "qoq_sales_growth": 81.1,
                "rd_pct": 6.2,
                "retained_earnings_ratio": 2.86,
                "roce": "32.0",
                "roe": "24.0",
                "valuation_alerts": ["Fails " "Current " "Ratio " "(< " "2.0)"],
            },
            "target": "5300.00",
            "target_high": "6300.00",
            "target_low": "3200.00",
            "target_median": "5300.00",
            "ticker": "HAL",
        },
        {
            "analyst_count": 28,
            "catalyst": "Defence electronics leader, "
            "securing major naval and "
            "surveillance command radar "
            "orders.",
            "earnings_growth": "+4.5%",
            "growth_pct": "+23.2%",
            "name": "Bharat Electronics",
            "price": "406.50",
            "rating": "None",
            "rec_score": None,
            "revenue_growth": "+11.7%",
            "screener": {
                "book_value": "32.8",
                "capex": 2044.8,
                "current_ratio": 1.9,
                "dividend_yield": "0.59",
                "graham_intrinsic_value": 711.4,
                "hyper_growth_warning": False,
                "is_bargain": False,
                "latest_quarter": "Mar 2026",
                "market_cap": "297143",
                "moat_status": "Strong (Wide " "Moat)",
                "ncav_per_share": 25.2,
                "net_current_assets": 18402.0,
                "owner_earnings": 6864.4,
                "pe_ratio": "49.0",
                "q_eps": "3.04",
                "q_net_profit": "2226",
                "q_sales": "10224",
                "qoq_profit_growth": 40.9,
                "qoq_sales_growth": 42.9,
                "rd_pct": 6.2,
                "retained_earnings_ratio": 2.86,
                "roce": "36.5",
                "roe": "27.6",
                "valuation_alerts": ["Fails " "Current " "Ratio " "(< " "2.0)"],
            },
            "target": "501.00",
            "target_high": "585.00",
            "target_low": "346.00",
            "target_median": "501.00",
            "ticker": "BEL",
        },
        {
            "analyst_count": 8,
            "catalyst": "High-end microwave sub-systems "
            "maker, critical supplier of "
            "radars and satellite payloads.",
            "earnings_growth": "+43.9%",
            "growth_pct": "+1.8%",
            "name": "Astra Microwave",
            "price": "1443.80",
            "rating": "Buy",
            "rec_score": 1.6,
            "revenue_growth": "+19.7%",
            "screener": {
                "book_value": "138",
                "capex": 97.6,
                "current_ratio": 4.31,
                "dividend_yield": "0.15",
                "graham_intrinsic_value": 2611.4,
                "hyper_growth_warning": False,
                "is_bargain": False,
                "latest_quarter": "Mar 2026",
                "market_cap": "13708",
                "moat_status": "Strong (Wide " "Moat)",
                "ncav_per_share": 134.4,
                "net_current_assets": 1276.0,
                "owner_earnings": 349.4,
                "pe_ratio": "71.0",
                "q_eps": "11.16",
                "q_net_profit": "106",
                "q_sales": "488",
                "qoq_profit_growth": 125.5,
                "qoq_sales_growth": 87.7,
                "rd_pct": 6.2,
                "retained_earnings_ratio": 2.86,
                "roce": "20.2",
                "roe": "16.0",
                "valuation_alerts": [],
            },
            "target": "1470.00",
            "target_high": "1665.00",
            "target_low": "1068.00",
            "target_median": "1470.00",
            "ticker": "ASTRAMICRO",
        },
    ],
    "big_cap_industries": [
        {
            "analyst_count": 31,
            "catalyst": "Heavy infrastructure leader, "
            "direct beneficiary of the "
            "government's ₹11.11 Lakh Cr "
            "CAPEX budget.",
            "earnings_growth": "-34.5%",
            "growth_pct": "+12.4%",
            "name": "Larsen & Toubro (L&T)",
            "price": "4049.30",
            "rating": "Buy",
            "rec_score": 1.7,
            "revenue_growth": "+11.7%",
            "screener": {
                "book_value": "794",
                "capex": 16552.4,
                "current_ratio": 1.61,
                "dividend_yield": "0.94",
                "graham_intrinsic_value": 6209.1,
                "hyper_growth_warning": False,
                "is_bargain": False,
                "latest_quarter": "Mar 2026",
                "market_cap": "557074",
                "moat_status": "Medium " "(Narrow " "Moat)",
                "ncav_per_share": 961.2,
                "net_current_assets": 132232.0,
                "owner_earnings": 18019.4,
                "pe_ratio": "34.0",
                "q_eps": "38.71",
                "q_net_profit": "6133",
                "q_sales": "82762",
                "qoq_profit_growth": 60.3,
                "qoq_sales_growth": 15.8,
                "rd_pct": 1.5,
                "retained_earnings_ratio": 2.86,
                "roce": "14.6",
                "roe": "15.9",
                "valuation_alerts": ["Fails " "Current " "Ratio " "(< " "2.0)"],
            },
            "target": "4550.00",
            "target_high": "4968.00",
            "target_low": "3600.00",
            "target_median": "4550.00",
            "ticker": "LT",
        },
        {
            "analyst_count": 32,
            "catalyst": "Consolidating 5G market share, "
            "scaling retail stores, and "
            "commissioning green energy "
            "gigafactories.",
            "earnings_growth": "-12.6%",
            "growth_pct": "+31.1%",
            "name": "Reliance Industries",
            "price": "1293.00",
            "rating": "Strong Buy",
            "rec_score": 1.3,
            "revenue_growth": "+12.5%",
            "screener": {
                "book_value": "668",
                "capex": 58811.8,
                "current_ratio": 0.65,
                "dividend_yield": "0.46",
                "graham_intrinsic_value": 1529.9,
                "hyper_growth_warning": False,
                "is_bargain": False,
                "latest_quarter": "Mar 2026",
                "market_cap": "1749757",
                "moat_status": "Weak/None",
                "ncav_per_share": -224.5,
                "net_current_assets": -303821.0,
                "owner_earnings": 55781.2,
                "pe_ratio": "22.5",
                "q_eps": "12.54",
                "q_net_profit": "20589",
                "q_sales": "294059",
                "qoq_profit_growth": -7.6,
                "qoq_sales_growth": 11.0,
                "rd_pct": 1.5,
                "retained_earnings_ratio": 2.86,
                "roce": "10.3",
                "roe": "8.91",
                "valuation_alerts": [
                    "Fails " "Current " "Ratio " "(< " "2.0)",
                    "Fails " "Debt " "Limit " "(Debt " "> " "Net " "Assets)",
                    "Weak/No " "Economic " "Moat",
                ],
            },
            "target": "1695.00",
            "target_high": "1910.00",
            "target_low": "1510.00",
            "target_median": "1695.00",
            "ticker": "RELIANCE",
        },
    ],
    "clean_energy": [
        {
            "analyst_count": 24,
            "catalyst": "Massive scaling in solar generation, "
            "microgrids, and leading India's EV "
            "charging network grid.",
            "earnings_growth": "-4.6%",
            "growth_pct": "+9.6%",
            "name": "Tata Power",
            "price": "393.55",
            "rating": "Hold",
            "rec_score": 2.5,
            "revenue_growth": "-12.8%",
            "screener": {
                "book_value": "124",
                "capex": 2980.0,
                "current_ratio": 0.95,
                "dividend_yield": "0.64",
                "graham_intrinsic_value": 275.8,
                "hyper_growth_warning": False,
                "is_bargain": False,
                "latest_quarter": "Mar 2026",
                "market_cap": "125753",
                "moat_status": "Weak/None",
                "ncav_per_share": -8.9,
                "net_current_assets": -2854.0,
                "owner_earnings": 8775.3,
                "pe_ratio": "33.1",
                "q_eps": "3.12",
                "q_net_profit": "1416",
                "q_sales": "14900",
                "qoq_profit_growth": 18.6,
                "qoq_sales_growth": 6.8,
                "rd_pct": 3.0,
                "retained_earnings_ratio": 2.86,
                "roce": "10.5",
                "roe": "10.1",
                "valuation_alerts": [
                    "Fails " "Current " "Ratio (< " "2.0)",
                    "Fails " "Debt " "Limit " "(Debt > " "Net " "Assets)",
                    "Fails P/E "
                    "Screen "
                    "(P/E 33.1 "
                    "> 15 & "
                    "Price > "
                    "Intrinsic)",
                    "Weak/No " "Economic " "Moat",
                ],
            },
            "target": "431.50",
            "target_high": "525.00",
            "target_low": "300.00",
            "target_median": "431.50",
            "ticker": "TATAPOWER",
        },
        {
            "analyst_count": 13,
            "catalyst": "Turnaround story, completely "
            "debt-free, dominating wind turbine "
            "supply with a record order book.",
            "earnings_growth": "-5.6%",
            "growth_pct": "+18.0%",
            "name": "Suzlon Energy",
            "price": "55.08",
            "rating": "Strong Buy",
            "rec_score": 1.4,
            "revenue_growth": "+44.9%",
            "screener": {
                "book_value": "6.96",
                "capex": 1098.6,
                "current_ratio": 1.83,
                "dividend_yield": "0.00",
                "graham_intrinsic_value": 191.9,
                "hyper_growth_warning": False,
                "is_bargain": False,
                "latest_quarter": "Mar 2026",
                "market_cap": "75061",
                "moat_status": "Strong (Wide Moat)",
                "ncav_per_share": 5.4,
                "net_current_assets": 7316.0,
                "owner_earnings": 3401.9,
                "pe_ratio": "23.7",
                "q_eps": "0.82",
                "q_net_profit": "1114",
                "q_sales": "5493",
                "qoq_profit_growth": 150.3,
                "qoq_sales_growth": 29.7,
                "rd_pct": 3.0,
                "retained_earnings_ratio": 2.86,
                "roce": "35.1",
                "roe": "40.6",
                "valuation_alerts": [
                    "Fails " "Current " "Ratio (< " "2.0)",
                    "No " "Dividend " "Yield",
                ],
            },
            "target": "65.00",
            "target_high": "75.00",
            "target_low": "52.00",
            "target_median": "65.00",
            "ticker": "SUZLON",
        },
        {
            "analyst_count": 8,
            "catalyst": "Developing the world's largest "
            "renewable energy park in Khavda, "
            "Gujarat (30 GW capacity target).",
            "earnings_growth": "+209.8%",
            "growth_pct": "-4.6%",
            "name": "Adani Green Energy",
            "price": "1485.70",
            "rating": "Strong Buy",
            "rec_score": 1.5,
            "revenue_growth": "+14.3%",
            "screener": {
                "book_value": "121",
                "capex": 700.4,
                "current_ratio": 0.97,
                "dividend_yield": "0.00",
                "graham_intrinsic_value": 563.9,
                "hyper_growth_warning": False,
                "is_bargain": False,
                "latest_quarter": "Mar 2026",
                "market_cap": "244721",
                "moat_status": "Weak/None",
                "ncav_per_share": -3.9,
                "net_current_assets": -642.0,
                "owner_earnings": 9639.2,
                "pe_ratio": "134",
                "q_eps": "2.41",
                "q_net_profit": "514",
                "q_sales": "3502",
                "qoq_profit_growth": 10180.0,
                "qoq_sales_growth": 33.8,
                "rd_pct": 3.0,
                "retained_earnings_ratio": 2.86,
                "roce": "7.39",
                "roe": "11.4",
                "valuation_alerts": [
                    "Fails " "Current " "Ratio (< " "2.0)",
                    "Fails " "Debt " "Limit " "(Debt > " "Net " "Assets)",
                    "Fails P/E "
                    "Screen "
                    "(P/E "
                    "134.0 > "
                    "15 & "
                    "Price > "
                    "Intrinsic)",
                    "No " "Dividend " "Yield",
                    "Weak/No " "Economic " "Moat",
                ],
            },
            "target": "1417.50",
            "target_high": "1730.00",
            "target_low": "1000.00",
            "target_median": "1417.50",
            "ticker": "ADANIGREEN",
        },
    ],
    "cybersecurity": [
        {
            "analyst_count": 43,
            "catalyst": "Expanding sovereign cloud and secure "
            "cyber command centers globally for "
            "enterprise clients.",
            "earnings_growth": "+12.2%",
            "growth_pct": "+36.5%",
            "name": "Tata Consultancy Services",
            "price": "2161.40",
            "rating": "Buy",
            "rec_score": 2.1,
            "revenue_growth": "+9.6%",
            "screener": {
                "book_value": "296",
                "capex": 14139.6,
                "current_ratio": 1.81,
                "dividend_yield": "2.96",
                "graham_intrinsic_value": 2927.4,
                "hyper_growth_warning": False,
                "is_bargain": False,
                "latest_quarter": "Mar 2026",
                "market_cap": "782013",
                "moat_status": "Strong (Wide " "Moat)",
                "ncav_per_share": 139.7,
                "net_current_assets": 50527.0,
                "owner_earnings": 41899.0,
                "pe_ratio": "15.0",
                "q_eps": "37.92",
                "q_net_profit": "13784",
                "q_sales": "70698",
                "qoq_profit_growth": 28.6,
                "qoq_sales_growth": 5.4,
                "rd_pct": 10.5,
                "retained_earnings_ratio": 2.86,
                "roce": "63.0",
                "roe": "51.8",
                "valuation_alerts": ["Fails " "Current " "Ratio (< " "2.0)"],
            },
            "target": "2950.00",
            "target_high": "3900.00",
            "target_low": "1775.00",
            "target_median": "2950.00",
            "ticker": "TCS",
        },
        {
            "analyst_count": None,
            "catalyst": "Surging enterprise adoption of their "
            "'Seqrite' cybersecurity platform and "
            "government IT contracts.",
            "earnings_growth": None,
            "growth_pct": None,
            "name": "Quick Heal Technologies",
            "price": "170.62",
            "rating": "None",
            "rec_score": None,
            "revenue_growth": "-25.2%",
            "screener": {
                "book_value": "80.5",
                "capex": 9.8,
                "current_ratio": 1.93,
                "dividend_yield": "0.00",
                "graham_intrinsic_value": -272.3,
                "hyper_growth_warning": True,
                "is_bargain": False,
                "latest_quarter": "Mar 2026",
                "market_cap": "926",
                "moat_status": "Weak/None",
                "ncav_per_share": 18.8,
                "net_current_assets": 102.0,
                "owner_earnings": -89.8,
                "pe_ratio": "80.5",
                "q_eps": "-3.68",
                "q_net_profit": "-20",
                "q_sales": "49",
                "qoq_profit_growth": -385.7,
                "qoq_sales_growth": -31.9,
                "rd_pct": 10.5,
                "retained_earnings_ratio": 1.2,
                "roce": "10.0",
                "roe": "10.0",
                "valuation_alerts": [
                    "Fails " "Current " "Ratio (< " "2.0)",
                    "Fails "
                    "P/E "
                    "Screen "
                    "(P/E "
                    "80.5 > "
                    "15 & "
                    "Price > "
                    "Intrinsic)",
                    "No " "Dividend " "Yield",
                    "Weak/No " "Economic " "Moat",
                    "Hyper-Growth "
                    "Warning: "
                    "Slowing "
                    "QoQ "
                    "sales at "
                    "P/E > "
                    "30",
                ],
            },
            "target": None,
            "target_high": None,
            "target_low": None,
            "target_median": None,
            "ticker": "QUICKHEAL",
        },
    ],
    "data_center_support": [
        {
            "analyst_count": 2,
            "catalyst": "Critical supplier of "
            "electrical distribution, smart "
            "grids, and high-efficiency "
            "cooling for data centers.",
            "earnings_growth": "-59.6%",
            "growth_pct": "+3.6%",
            "name": "Schneider Electric Infra",
            "price": "1105.70",
            "rating": "Strong Buy",
            "rec_score": 1.0,
            "revenue_growth": "+0.5%",
            "screener": {
                "capex": 0.0,
                "current_ratio": 2.0,
                "graham_intrinsic_value": 0.0,
                "hyper_growth_warning": False,
                "is_bargain": False,
                "moat_status": "Weak/None",
                "ncav_per_share": 0,
                "net_current_assets": 0.0,
                "owner_earnings": 0.0,
                "rd_pct": 1.5,
                "retained_earnings_ratio": 1.2,
                "valuation_alerts": [
                    "No " "Dividend " "Yield",
                    "Weak/No " "Economic " "Moat",
                ],
            },
            "target": "1145.00",
            "target_high": "1320.00",
            "target_low": "970.00",
            "target_median": "1145.00",
            "ticker": "SCHNEIDER",
        },
        {
            "analyst_count": 2,
            "catalyst": "Expanding optical fiber and "
            "cable capacities to meet "
            "hyper-scale data center "
            "interconnect demands.",
            "earnings_growth": None,
            "growth_pct": "-6.2%",
            "name": "Sterlite Technologies (STL)",
            "price": "583.65",
            "rating": "None",
            "rec_score": None,
            "revenue_growth": "+1285.6%",
            "screener": {
                "book_value": "46.5",
                "capex": 288.2,
                "current_ratio": 1.35,
                "dividend_yield": "0.00",
                "graham_intrinsic_value": 182.5,
                "hyper_growth_warning": True,
                "is_bargain": False,
                "latest_quarter": "Mar 2026",
                "market_cap": "28492",
                "moat_status": "Weak/None",
                "ncav_per_share": 15.4,
                "net_current_assets": 753.0,
                "owner_earnings": 103.2,
                "pe_ratio": "598",
                "q_eps": "1.21",
                "q_net_profit": "59",
                "q_sales": "1441",
                "qoq_sales_growth": 14.6,
                "rd_pct": 1.5,
                "retained_earnings_ratio": 2.86,
                "roce": "7.75",
                "roe": "2.24",
                "valuation_alerts": [
                    "Fails " "Current " "Ratio " "(< " "2.0)",
                    "Fails " "Debt " "Limit " "(Debt " "> " "Net " "Assets)",
                    "Fails "
                    "P/E "
                    "Screen "
                    "(P/E "
                    "598.0 "
                    "> "
                    "15 "
                    "& "
                    "Price "
                    "> "
                    "Intrinsic)",
                    "No " "Dividend " "Yield",
                    "Weak/No " "Economic " "Moat",
                    "Hyper-Growth "
                    "Warning: "
                    "Slowing "
                    "QoQ "
                    "sales "
                    "at "
                    "P/E "
                    "> "
                    "30",
                ],
            },
            "target": "547.50",
            "target_high": "655.00",
            "target_low": "440.00",
            "target_median": "547.50",
            "ticker": "STLTECH",
        },
        {
            "analyst_count": 3,
            "catalyst": "Real-estate developer "
            "transitioning commercial "
            "properties into major data "
            "center hubs in NCR.",
            "earnings_growth": "+20.5%",
            "growth_pct": "+30.9%",
            "name": "Anant Raj Ltd",
            "price": "534.75",
            "rating": "None",
            "rec_score": None,
            "revenue_growth": "+19.6%",
            "screener": {
                "book_value": "161",
                "capex": 129.4,
                "current_ratio": 12.16,
                "dividend_yield": "0.14",
                "graham_intrinsic_value": 301.2,
                "hyper_growth_warning": True,
                "is_bargain": False,
                "latest_quarter": "Mar 2026",
                "market_cap": "19244",
                "moat_status": "Weak/None",
                "ncav_per_share": 123.8,
                "net_current_assets": 4454.0,
                "owner_earnings": 521.1,
                "pe_ratio": "34.7",
                "q_eps": "4.07",
                "q_net_profit": "149",
                "q_sales": "647",
                "qoq_profit_growth": 3.5,
                "qoq_sales_growth": 0.8,
                "rd_pct": 1.5,
                "retained_earnings_ratio": 2.86,
                "roce": "12.1",
                "roe": "11.2",
                "valuation_alerts": [
                    "Fails "
                    "P/E "
                    "Screen "
                    "(P/E "
                    "34.7 "
                    "> "
                    "15 "
                    "& "
                    "Price "
                    "> "
                    "Intrinsic)",
                    "Weak/No " "Economic " "Moat",
                    "Hyper-Growth "
                    "Warning: "
                    "Slowing "
                    "QoQ "
                    "sales "
                    "at "
                    "P/E "
                    "> "
                    "30",
                ],
            },
            "target": "700.00",
            "target_high": "800.00",
            "target_low": "650.00",
            "target_median": "700.00",
            "ticker": "ANANTRAJ",
        },
    ],
    "fmcg": [
        {
            "analyst_count": 26,
            "catalyst": "PepsiCo's dominant bottler, expanding into "
            "newer territories and scaling dairy/juice "
            "products.",
            "earnings_growth": "+20.0%",
            "growth_pct": "+13.7%",
            "name": "Varun Beverages (PepsiCo)",
            "price": "522.20",
            "rating": "None",
            "rec_score": None,
            "revenue_growth": "+18.1%",
            "screener": {
                "book_value": "57.9",
                "capex": 1314.8,
                "current_ratio": 2.41,
                "dividend_yield": "0.29",
                "graham_intrinsic_value": 603.7,
                "hyper_growth_warning": False,
                "is_bargain": False,
                "latest_quarter": "Mar 2026",
                "market_cap": "176624",
                "moat_status": "Strong (Wide Moat)",
                "ncav_per_share": 14.4,
                "net_current_assets": 4883.0,
                "owner_earnings": 2401.8,
                "pe_ratio": "55.5",
                "q_eps": "2.58",
                "q_net_profit": "879",
                "q_sales": "6574",
                "qoq_profit_growth": 238.1,
                "qoq_sales_growth": 56.4,
                "rd_pct": 1.5,
                "retained_earnings_ratio": 2.86,
                "roce": "19.7",
                "roe": "16.2",
                "valuation_alerts": [],
            },
            "target": "594.00",
            "target_high": "657.00",
            "target_low": "422.00",
            "target_median": "594.00",
            "ticker": "VBL",
        },
        {
            "analyst_count": 29,
            "catalyst": "Premiumization strategy in foods & beverages, "
            "high-growth acquisitions (Capital Foods, "
            "Organic India).",
            "earnings_growth": "+21.5%",
            "growth_pct": "+22.6%",
            "name": "Tata Consumer Products",
            "price": "1100.70",
            "rating": "Buy",
            "rec_score": 1.8,
            "revenue_growth": "+17.9%",
            "screener": {
                "book_value": "220",
                "capex": 1086.8,
                "current_ratio": 1.07,
                "dividend_yield": "0.91",
                "graham_intrinsic_value": 357.9,
                "hyper_growth_warning": False,
                "is_bargain": False,
                "latest_quarter": "Mar 2026",
                "market_cap": "108930",
                "moat_status": "Weak/None",
                "ncav_per_share": 6.7,
                "net_current_assets": 664.0,
                "owner_earnings": 834.8,
                "pe_ratio": "70.9",
                "q_eps": "4.24",
                "q_net_profit": "424",
                "q_sales": "5434",
                "qoq_profit_growth": 10.1,
                "qoq_sales_growth": 6.3,
                "rd_pct": 1.5,
                "retained_earnings_ratio": 2.86,
                "roce": "9.24",
                "roe": "7.35",
                "valuation_alerts": [
                    "Fails Current " "Ratio (< 2.0)",
                    "Fails Debt Limit " "(Debt > Net " "Assets)",
                    "Fails P/E Screen " "(P/E 70.9 > 15 & " "Price > " "Intrinsic)",
                    "Weak/No Economic " "Moat",
                ],
            },
            "target": "1350.00",
            "target_high": "1460.00",
            "target_low": "1124.00",
            "target_median": "1350.00",
            "ticker": "TATACONSUM",
        },
        {
            "analyst_count": 33,
            "catalyst": "Resilient cigarette margins funding rapid "
            "expansion of high-margin FMCG brands, direct "
            "rural boost play.",
            "earnings_growth": "-72.7%",
            "growth_pct": "+15.7%",
            "name": "ITC Ltd",
            "price": "285.10",
            "rating": "Hold",
            "rec_score": 2.6,
            "revenue_growth": "-5.0%",
            "screener": {
                "book_value": "57.9",
                "capex": 3565.0,
                "current_ratio": 1.67,
                "dividend_yield": "5.09",
                "graham_intrinsic_value": 318.2,
                "hyper_growth_warning": False,
                "is_bargain": False,
                "latest_quarter": "Mar 2026",
                "market_cap": "357215",
                "moat_status": "Strong (Wide Moat)",
                "ncav_per_share": 10.2,
                "net_current_assets": 12734.0,
                "owner_earnings": 18506.9,
                "pe_ratio": "17.1",
                "q_eps": "4.30",
                "q_net_profit": "5470",
                "q_sales": "17825",
                "qoq_profit_growth": 9.0,
                "qoq_sales_growth": -11.1,
                "rd_pct": 1.5,
                "retained_earnings_ratio": 2.86,
                "roce": "38.9",
                "roe": "29.3",
                "valuation_alerts": ["Fails Current " "Ratio (< 2.0)"],
            },
            "target": "330.00",
            "target_high": "486.00",
            "target_low": "290.00",
            "target_median": "330.00",
            "ticker": "ITC",
        },
    ],
    "logistics_heavy_capital": [
        {
            "analyst_count": 17,
            "catalyst": "Dominant railway container "
            "carrier, major beneficiary "
            "of the ₹10,000 crore "
            "container manufacturing "
            "scheme.",
            "earnings_growth": "-12.0%",
            "growth_pct": "+13.3%",
            "name": "Container Corporation of India",
            "price": "450.20",
            "rating": "Buy",
            "rec_score": 2.5,
            "revenue_growth": "-1.1%",
            "screener": {
                "book_value": "170",
                "capex": 452.6,
                "current_ratio": 4.75,
                "dividend_yield": "2.04",
                "graham_intrinsic_value": 255.3,
                "hyper_growth_warning": False,
                "is_bargain": False,
                "latest_quarter": "Mar " "2026",
                "market_cap": "34288",
                "moat_status": "Weak/None",
                "ncav_per_share": 62.5,
                "net_current_assets": 4759.0,
                "owner_earnings": 680.6,
                "pe_ratio": "27.6",
                "q_eps": "3.45",
                "q_net_profit": "264",
                "q_sales": "2263",
                "qoq_profit_growth": -21.2,
                "qoq_sales_growth": -1.9,
                "rd_pct": 1.5,
                "retained_earnings_ratio": 2.86,
                "roce": "12.4",
                "roe": "9.81",
                "valuation_alerts": [
                    "Fails "
                    "P/E "
                    "Screen "
                    "(P/E "
                    "27.6 "
                    "> "
                    "15 "
                    "& "
                    "Price "
                    "> "
                    "Intrinsic)",
                    "Weak/No " "Economic " "Moat",
                ],
            },
            "target": "510.00",
            "target_high": "682.00",
            "target_low": "456.00",
            "target_median": "510.00",
            "ticker": "CONCOR",
        },
        {
            "analyst_count": 21,
            "catalyst": "State-owned heavy power "
            "equipment giant, expanding "
            "local container "
            "manufacturing and green "
            "energy grids.",
            "earnings_growth": "+156.4%",
            "growth_pct": "+9.3%",
            "name": "Bharat Heavy Electricals",
            "price": "378.75",
            "rating": "Hold",
            "rec_score": 2.9,
            "revenue_growth": "+36.9%",
            "screener": {
                "book_value": "75.1",
                "capex": 2462.0,
                "current_ratio": 1.73,
                "dividend_yield": "0.13",
                "graham_intrinsic_value": 868.1,
                "hyper_growth_warning": False,
                "is_bargain": False,
                "latest_quarter": "Mar " "2026",
                "market_cap": "131883",
                "moat_status": "Weak/None",
                "ncav_per_share": 87.7,
                "net_current_assets": 30538.0,
                "owner_earnings": 3353.0,
                "pe_ratio": "82.4",
                "q_eps": "3.71",
                "q_net_profit": "1290",
                "q_sales": "12310",
                "qoq_profit_growth": 230.8,
                "qoq_sales_growth": 45.3,
                "rd_pct": 1.5,
                "retained_earnings_ratio": 2.86,
                "roce": "8.51",
                "roe": "6.29",
                "valuation_alerts": [
                    "Fails " "Current " "Ratio " "(< " "2.0)",
                    "Weak/No " "Economic " "Moat",
                ],
            },
            "target": "414.00",
            "target_high": "460.00",
            "target_low": "140.00",
            "target_median": "414.00",
            "ticker": "BHEL",
        },
        {
            "analyst_count": 23,
            "catalyst": "Leading heavy engine "
            "maker, supplying power "
            "backups and engines for "
            "logistics and railway "
            "expansion.",
            "earnings_growth": "+22.7%",
            "growth_pct": "+3.2%",
            "name": "Cummins India",
            "price": "5621.50",
            "rating": "Hold",
            "rec_score": 2.7,
            "revenue_growth": "+21.9%",
            "screener": {
                "book_value": "306",
                "capex": 602.2,
                "current_ratio": 2.39,
                "dividend_yield": "1.17",
                "graham_intrinsic_value": 1733.8,
                "hyper_growth_warning": False,
                "is_bargain": False,
                "latest_quarter": "Mar " "2026",
                "market_cap": "155828",
                "moat_status": "Strong " "(Wide " "Moat)",
                "ncav_per_share": 139.9,
                "net_current_assets": 3877.0,
                "owner_earnings": 1996.8,
                "pe_ratio": "64.3",
                "q_eps": "23.43",
                "q_net_profit": "649",
                "q_sales": "3011",
                "qoq_profit_growth": 33.5,
                "qoq_sales_growth": -1.4,
                "rd_pct": 1.5,
                "retained_earnings_ratio": 2.86,
                "roce": "39.5",
                "roe": "30.2",
                "valuation_alerts": [
                    "Fails "
                    "P/E "
                    "Screen "
                    "(P/E "
                    "64.3 "
                    "> "
                    "15 "
                    "& "
                    "Price "
                    "> "
                    "Intrinsic)"
                ],
            },
            "target": "5800.00",
            "target_high": "7100.00",
            "target_low": "3420.00",
            "target_median": "5800.00",
            "ticker": "CUMMINSIND",
        },
    ],
    "macro_indicators": [
        {
            "analyst_count": None,
            "catalyst": "Passive index fund tracking the "
            "broader GVA growth of India's "
            "manufacturing sector.",
            "earnings_growth": None,
            "growth_pct": None,
            "name": "ICICI Pru Nifty India Manufacturing " "ETF",
            "price": "100.50",
            "rating": "N/A",
            "rec_score": None,
            "revenue_growth": None,
            "screener": {
                "market_cap": "N/A",
                "pe_ratio": "N/A",
                "roce": "N/A",
                "roe": "N/A",
                "valuation_alerts": [],
            },
            "target": None,
            "target_high": None,
            "target_low": None,
            "target_median": None,
            "ticker": "MANUETF",
        },
        {
            "analyst_count": None,
            "catalyst": "Passive index fund tracking "
            "manufacturing sector performance "
            "under PLI schemes.",
            "earnings_growth": None,
            "growth_pct": None,
            "name": "HDFC Nifty India Manufacturing ETF",
            "price": "52.40",
            "rating": "N/A",
            "rec_score": None,
            "revenue_growth": None,
            "screener": {
                "market_cap": "N/A",
                "pe_ratio": "N/A",
                "roce": "N/A",
                "roe": "N/A",
                "valuation_alerts": [],
            },
            "target": None,
            "target_high": None,
            "target_low": None,
            "target_median": None,
            "ticker": "HDFCMANETF",
        },
    ],
    "manufacturing_electronics": [
        {
            "analyst_count": 29,
            "catalyst": "Leader in electronic "
            "assembly (mobile, "
            "laptop, LED TV), heavily "
            "subsidized under "
            "manufacturing PLI.",
            "earnings_growth": "-36.1%",
            "growth_pct": "+3.1%",
            "name": "Dixon Technologies",
            "price": "11546.00",
            "rating": "Buy",
            "rec_score": 2.3,
            "revenue_growth": "+2.1%",
            "screener": {
                "book_value": "769",
                "capex": 2102.2,
                "current_ratio": 0.99,
                "dividend_yield": "0.07",
                "graham_intrinsic_value": 3120.6,
                "hyper_growth_warning": False,
                "is_bargain": False,
                "latest_quarter": "Mar " "2026",
                "market_cap": "70530",
                "moat_status": "Strong " "(Wide " "Moat)",
                "ncav_per_share": -12.9,
                "net_current_assets": -79.0,
                "owner_earnings": -830.7,
                "pe_ratio": "49.0",
                "q_eps": "42.17",
                "q_net_profit": "298",
                "q_sales": "10511",
                "qoq_profit_growth": -7.2,
                "qoq_sales_growth": -1.5,
                "rd_pct": 1.5,
                "retained_earnings_ratio": 2.86,
                "roce": "42.0",
                "roe": "37.4",
                "valuation_alerts": [
                    "Fails " "Current " "Ratio " "(< " "2.0)",
                    "Fails " "Debt " "Limit " "(Debt " "> " "Net " "Assets)",
                    "Fails "
                    "P/E "
                    "Screen "
                    "(P/E "
                    "49.0 "
                    "> "
                    "15 "
                    "& "
                    "Price "
                    "> "
                    "Intrinsic)",
                ],
            },
            "target": "11900.00",
            "target_high": "15200.00",
            "target_low": "8157.00",
            "target_median": "11900.00",
            "ticker": "DIXON",
        },
        {
            "analyst_count": 22,
            "catalyst": "High-end electronics and "
            "PCBA manufacturing, "
            "setting up a "
            "state-of-the-art "
            "semiconductor OSAT "
            "plant.",
            "earnings_growth": "-26.3%",
            "growth_pct": "+14.3%",
            "name": "Kaynes Technology",
            "price": "3076.90",
            "rating": "Hold",
            "rec_score": 3.0,
            "revenue_growth": "+26.2%",
            "screener": {
                "book_value": "708",
                "capex": 248.6,
                "current_ratio": 3.68,
                "dividend_yield": "0.00",
                "graham_intrinsic_value": 3184.7,
                "hyper_growth_warning": False,
                "is_bargain": False,
                "latest_quarter": "Mar " "2026",
                "market_cap": "20626",
                "moat_status": "Weak/None",
                "ncav_per_share": 492.1,
                "net_current_assets": 3299.0,
                "owner_earnings": 188.4,
                "pe_ratio": "56.4",
                "q_eps": "13.61",
                "q_net_profit": "91",
                "q_sales": "1243",
                "qoq_profit_growth": 18.2,
                "qoq_sales_growth": 54.6,
                "rd_pct": 1.5,
                "retained_earnings_ratio": 2.86,
                "roce": "13.2",
                "roe": "9.64",
                "valuation_alerts": [
                    "No " "Dividend " "Yield",
                    "Weak/No " "Economic " "Moat",
                ],
            },
            "target": "3516.50",
            "target_high": "4060.00",
            "target_low": "2647.00",
            "target_median": "3516.50",
            "ticker": "KAYNES",
        },
        {
            "analyst_count": 19,
            "catalyst": "Partnering on a $1B "
            "semiconductor fab, "
            "strong order pipeline in "
            "railways and power grid "
            "equipment.",
            "earnings_growth": "+30.5%",
            "growth_pct": "+1.7%",
            "name": "CG Power & Industrial",
            "price": "914.45",
            "rating": "Buy",
            "rec_score": 2.1,
            "revenue_growth": "+25.0%",
            "screener": {
                "book_value": "50.6",
                "capex": 688.4,
                "current_ratio": 2.07,
                "dividend_yield": "0.14",
                "graham_intrinsic_value": 234.8,
                "hyper_growth_warning": True,
                "is_bargain": False,
                "latest_quarter": "Mar " "2026",
                "market_cap": "144022",
                "moat_status": "Strong " "(Wide " "Moat)",
                "ncav_per_share": 31.1,
                "net_current_assets": 4902.0,
                "owner_earnings": 773.0,
                "pe_ratio": "117",
                "q_eps": "2.32",
                "q_net_profit": "363",
                "q_sales": "3442",
                "qoq_profit_growth": 27.8,
                "qoq_sales_growth": 8.4,
                "rd_pct": 1.5,
                "retained_earnings_ratio": 2.86,
                "roce": "27.0",
                "roe": "20.8",
                "valuation_alerts": [
                    "Fails "
                    "P/E "
                    "Screen "
                    "(P/E "
                    "117.0 "
                    "> "
                    "15 "
                    "& "
                    "Price "
                    "> "
                    "Intrinsic)",
                    "Hyper-Growth "
                    "Warning: "
                    "Slowing "
                    "QoQ "
                    "sales "
                    "at "
                    "P/E "
                    "> "
                    "30",
                ],
            },
            "target": "930.00",
            "target_high": "1100.00",
            "target_low": "502.00",
            "target_median": "930.00",
            "ticker": "CGPOWER",
        },
    ],
    "semiconductors_equipment": [
        {
            "analyst_count": None,
            "catalyst": "Engineering design "
            "services for "
            "semiconductor equipment "
            "makers under India "
            "Semiconductor Mission "
            "(ISM) 2.0.",
            "earnings_growth": None,
            "growth_pct": None,
            "name": "ASM Technologies",
            "price": "1250.00",
            "rating": "N/A",
            "rec_score": None,
            "revenue_growth": None,
            "screener": {},
            "target": None,
            "target_high": None,
            "target_low": None,
            "target_median": None,
            "ticker": "ASMTEC",
        },
        {
            "analyst_count": None,
            "catalyst": "Power semiconductor "
            "device supplier, building "
            "new SiC fab facility "
            "under semiconductor PLI.",
            "earnings_growth": None,
            "growth_pct": None,
            "name": "RIR Power Electronics",
            "price": "1840.00",
            "rating": "N/A",
            "rec_score": None,
            "revenue_growth": None,
            "screener": {},
            "target": None,
            "target_high": None,
            "target_low": None,
            "target_median": None,
            "ticker": "RIRPOWER",
        },
        {
            "analyst_count": None,
            "catalyst": "First semiconductor OSAT "
            "and assembly facility "
            "listed, expanding IC "
            "testing capabilities.",
            "earnings_growth": None,
            "growth_pct": None,
            "name": "SPEL Semiconductor",
            "price": "115.00",
            "rating": "N/A",
            "rec_score": None,
            "revenue_growth": None,
            "screener": {},
            "target": None,
            "target_high": None,
            "target_low": None,
            "target_median": None,
            "ticker": "SPEL",
        },
    ],
    "sports_athleisure": [
        {
            "analyst_count": 21,
            "catalyst": "Exclusive retail rights for Fila "
            "and Foot Locker in India, "
            "expanding athleisure footprint "
            "rapidly.",
            "earnings_growth": "+23.2%",
            "growth_pct": "+24.9%",
            "name": "Metro Brands Ltd",
            "price": "1000.50",
            "rating": "None",
            "rec_score": None,
            "revenue_growth": "+20.3%",
            "screener": {
                "book_value": "73.1",
                "capex": 154.6,
                "current_ratio": 2.96,
                "dividend_yield": "0.55",
                "graham_intrinsic_value": 316.7,
                "hyper_growth_warning": True,
                "is_bargain": False,
                "latest_quarter": "Mar 2026",
                "market_cap": "27270",
                "moat_status": "Strong (Wide " "Moat)",
                "ncav_per_share": 32.6,
                "net_current_assets": 888.0,
                "owner_earnings": 443.0,
                "pe_ratio": "66.3",
                "q_eps": "4.28",
                "q_net_profit": "118",
                "q_sales": "773",
                "qoq_profit_growth": -9.2,
                "qoq_sales_growth": -4.7,
                "rd_pct": 1.5,
                "retained_earnings_ratio": 2.86,
                "roce": "20.2",
                "roe": "22.2",
                "valuation_alerts": [
                    "Fails " "Debt " "Limit " "(Debt " "> " "Net " "Assets)",
                    "Fails "
                    "P/E "
                    "Screen "
                    "(P/E "
                    "66.3 "
                    "> 15 "
                    "& "
                    "Price "
                    "> "
                    "Intrinsic)",
                    "Hyper-Growth "
                    "Warning: "
                    "Slowing "
                    "QoQ "
                    "sales "
                    "at "
                    "P/E "
                    "> "
                    "30",
                ],
            },
            "target": "1250.00",
            "target_high": "1400.00",
            "target_low": "1040.00",
            "target_median": "1250.00",
            "ticker": "METROBRAND",
        },
        {
            "analyst_count": 7,
            "catalyst": "Dominant direct-to-consumer "
            "sports footwear brand in "
            "tier-2/3 cities, major "
            "beneficiary of fitness trends.",
            "earnings_growth": "+25.2%",
            "growth_pct": "+28.8%",
            "name": "Campus Activewear",
            "price": "238.40",
            "rating": "None",
            "rec_score": None,
            "revenue_growth": "+12.3%",
            "screener": {
                "book_value": "0.63",
                "capex": 67.6,
                "current_ratio": 2.59,
                "dividend_yield": "0.63",
                "graham_intrinsic_value": 69.6,
                "hyper_growth_warning": False,
                "is_bargain": False,
                "latest_quarter": "Jun 2022",
                "market_cap": "7285",
                "moat_status": "Strong (Wide " "Moat)",
                "ncav_per_share": 12.8,
                "net_current_assets": 392.0,
                "owner_earnings": 71.5,
                "pe_ratio": "53.6",
                "q_eps": "0.94",
                "q_net_profit": "29",
                "q_sales": "338",
                "qoq_profit_growth": -27.5,
                "qoq_sales_growth": -4.0,
                "rd_pct": 1.5,
                "retained_earnings_ratio": 2.86,
                "roce": "31.8",
                "roe": "29.5",
                "valuation_alerts": [
                    "Fails "
                    "P/E "
                    "Screen "
                    "(P/E "
                    "53.6 "
                    "> 15 "
                    "& "
                    "Price "
                    "> "
                    "Intrinsic)"
                ],
            },
            "target": "307.00",
            "target_high": "349.00",
            "target_low": "247.00",
            "target_median": "307.00",
            "ticker": "CAMPUS",
        },
        {
            "analyst_count": 26,
            "catalyst": "Jockey master franchise holder, "
            "expanding sports shorts, tees, "
            "and athleisure wear into rural "
            "hubs.",
            "earnings_growth": "+9.0%",
            "growth_pct": "+7.1%",
            "name": "Page Industries",
            "price": "38625.00",
            "rating": "Hold",
            "rec_score": 2.7,
            "revenue_growth": "+14.1%",
            "screener": {
                "capex": 0.0,
                "current_ratio": 2.0,
                "graham_intrinsic_value": 0.0,
                "hyper_growth_warning": False,
                "is_bargain": False,
                "moat_status": "Weak/None",
                "ncav_per_share": 0,
                "net_current_assets": 0.0,
                "owner_earnings": 0.0,
                "rd_pct": 1.5,
                "retained_earnings_ratio": 1.2,
                "valuation_alerts": [
                    "No " "Dividend " "Yield",
                    "Weak/No " "Economic " "Moat",
                ],
            },
            "target": "41350.00",
            "target_high": "47700.00",
            "target_low": "31000.00",
            "target_median": "41350.00",
            "ticker": "PAGEIND",
        },
        {
            "analyst_count": 10,
            "catalyst": "Auto-discovered via media radar. "
            "Catalyst: Relaxo Footwears Ltd "
            "(RELAXO) Share Price",
            "earnings_growth": "+20.5%",
            "growth_pct": "+13.2%",
            "name": "Relaxo Footwears Limited",
            "price": "342.65",
            "rating": "Hold",
            "rec_score": 2.8,
            "revenue_growth": "+8.0%",
            "screener": {
                "capex": 0.0,
                "current_ratio": 2.0,
                "graham_intrinsic_value": 0.0,
                "hyper_growth_warning": False,
                "is_bargain": False,
                "moat_status": "Weak/None",
                "ncav_per_share": 0,
                "net_current_assets": 0.0,
                "owner_earnings": 0.0,
                "rd_pct": 1.5,
                "retained_earnings_ratio": 1.2,
                "valuation_alerts": [
                    "No " "Dividend " "Yield",
                    "Weak/No " "Economic " "Moat",
                ],
            },
            "target": "388.00",
            "target_high": "440.00",
            "target_low": "280.00",
            "target_median": "388.00",
            "ticker": "RELAXO",
        },
    ],
    "surveillance_security": [
        {
            "analyst_count": 4,
            "catalyst": "CCTV market leader (35%+ "
            "share) newly listed, scaling "
            "domestic camera "
            "manufacturing under PLI.",
            "earnings_growth": "+187.4%",
            "growth_pct": "-5.6%",
            "name": "Aditya Infotech (CP PLUS)",
            "price": "3375.90",
            "rating": "Strong Buy",
            "rec_score": 1.0,
            "revenue_growth": "+45.5%",
            "screener": {
                "book_value": "159",
                "capex": 284.4,
                "current_ratio": 1.6,
                "dividend_yield": "0.00",
                "graham_intrinsic_value": 3337.3,
                "hyper_growth_warning": False,
                "is_bargain": False,
                "latest_quarter": "Mar " "2026",
                "market_cap": "39785",
                "moat_status": "Strong " "(Wide " "Moat)",
                "ncav_per_share": 98.3,
                "net_current_assets": 1159.0,
                "owner_earnings": 406.0,
                "pe_ratio": "108",
                "q_eps": "14.36",
                "q_net_profit": "169",
                "q_sales": "1422",
                "qoq_profit_growth": 76.0,
                "qoq_sales_growth": 24.8,
                "rd_pct": 1.5,
                "retained_earnings_ratio": 2.86,
                "roce": "29.6",
                "roe": "25.4",
                "valuation_alerts": [
                    "Fails " "Current " "Ratio " "(< " "2.0)",
                    "No " "Dividend " "Yield",
                ],
            },
            "target": "3188.00",
            "target_high": "3806.00",
            "target_low": "3044.00",
            "target_median": "3188.00",
            "ticker": "CPPLUS",
        },
        {
            "analyst_count": 29,
            "catalyst": "Primary EMS contract "
            "manufacturer producing CCTVs "
            "and DVRs for CP Plus and "
            "others under PLI.",
            "earnings_growth": "-36.1%",
            "growth_pct": "+3.1%",
            "name": "Dixon Technologies",
            "price": "11546.00",
            "rating": "Buy",
            "rec_score": 2.3,
            "revenue_growth": "+2.1%",
            "screener": {
                "book_value": "769",
                "capex": 2102.2,
                "current_ratio": 0.99,
                "dividend_yield": "0.07",
                "graham_intrinsic_value": 3120.6,
                "hyper_growth_warning": False,
                "is_bargain": False,
                "latest_quarter": "Mar " "2026",
                "market_cap": "70530",
                "moat_status": "Strong " "(Wide " "Moat)",
                "ncav_per_share": -12.9,
                "net_current_assets": -79.0,
                "owner_earnings": -830.7,
                "pe_ratio": "49.0",
                "q_eps": "42.17",
                "q_net_profit": "298",
                "q_sales": "10511",
                "qoq_profit_growth": -7.2,
                "qoq_sales_growth": -1.5,
                "rd_pct": 1.5,
                "retained_earnings_ratio": 2.86,
                "roce": "42.0",
                "roe": "37.4",
                "valuation_alerts": [
                    "Fails " "Current " "Ratio " "(< " "2.0)",
                    "Fails " "Debt " "Limit " "(Debt " "> " "Net " "Assets)",
                    "Fails "
                    "P/E "
                    "Screen "
                    "(P/E "
                    "49.0 "
                    "> "
                    "15 "
                    "& "
                    "Price "
                    "> "
                    "Intrinsic)",
                ],
            },
            "target": "11900.00",
            "target_high": "15200.00",
            "target_low": "8157.00",
            "target_median": "11900.00",
            "ticker": "DIXON",
        },
        {
            "analyst_count": 1,
            "catalyst": "System integrator winning "
            "smart/safe city surveillance "
            "projects, managing master "
            "command centers.",
            "earnings_growth": None,
            "growth_pct": "+53.3%",
            "name": "Allied Digital Services",
            "price": "117.44",
            "rating": "None",
            "rec_score": None,
            "revenue_growth": "+31.0%",
            "screener": {
                "book_value": "109",
                "capex": 53.6,
                "current_ratio": 2.56,
                "dividend_yield": "1.28",
                "graham_intrinsic_value": -59.8,
                "hyper_growth_warning": False,
                "is_bargain": False,
                "latest_quarter": "Mar " "2026",
                "market_cap": "664",
                "moat_status": "Weak/None",
                "ncav_per_share": 85.4,
                "net_current_assets": 483.0,
                "owner_earnings": -56.3,
                "pe_ratio": "18.5",
                "q_eps": "-0.60",
                "q_net_profit": "-3.39",
                "q_sales": "267.77",
                "qoq_profit_growth": -124.4,
                "qoq_sales_growth": 8.2,
                "rd_pct": 1.5,
                "retained_earnings_ratio": 1.2,
                "roce": "7.32",
                "roe": "5.92",
                "valuation_alerts": [
                    "Fails "
                    "P/E "
                    "Screen "
                    "(P/E "
                    "18.5 "
                    "> "
                    "15 "
                    "& "
                    "Price "
                    "> "
                    "Intrinsic)",
                    "Weak/No " "Economic " "Moat",
                ],
            },
            "target": "180.00",
            "target_high": "180.00",
            "target_low": "180.00",
            "target_median": "180.00",
            "ticker": "ADSL",
        },
        {
            "analyst_count": 2,
            "catalyst": "Pioneer in tactical and "
            "mapping drone systems, "
            "primary supplier for Indian "
            "Army and police borders.",
            "earnings_growth": None,
            "growth_pct": "+18.6%",
            "name": "IdeaForge Technology",
            "price": "869.10",
            "rating": "None",
            "rec_score": None,
            "revenue_growth": "+594.4%",
            "screener": {
                "book_value": "138",
                "capex": 28.2,
                "current_ratio": 3.84,
                "dividend_yield": "0.00",
                "graham_intrinsic_value": 3243.2,
                "hyper_growth_warning": False,
                "is_bargain": False,
                "latest_quarter": "Mar " "2026",
                "market_cap": "3771",
                "moat_status": "Weak/None",
                "ncav_per_share": 76.1,
                "net_current_assets": 330.0,
                "owner_earnings": 218.5,
                "pe_ratio": "138",
                "q_eps": "13.86",
                "q_net_profit": "60",
                "q_sales": "141",
                "qoq_sales_growth": 340.6,
                "rd_pct": 1.5,
                "retained_earnings_ratio": 2.86,
                "roce": "10.0",
                "roe": "10.0",
                "valuation_alerts": [
                    "No " "Dividend " "Yield",
                    "Weak/No " "Economic " "Moat",
                ],
            },
            "target": "1031.00",
            "target_high": "1187.00",
            "target_low": "875.00",
            "target_median": "1031.00",
            "ticker": "IDEAFORGE",
        },
        {
            "analyst_count": 12,
            "catalyst": "Auto-discovered via media "
            "radar. Catalyst: Zen "
            "Technologies climbs 4% on "
            "launch of anti-drone smart "
            "border system",
            "earnings_growth": "+19.2%",
            "growth_pct": "+39.7%",
            "name": "Zensar Technologies Limited",
            "price": "452.80",
            "rating": "None",
            "rec_score": None,
            "revenue_growth": "+6.7%",
            "screener": {
                "book_value": "207",
                "capex": 290.0,
                "current_ratio": 2.15,
                "dividend_yield": "2.87",
                "graham_intrinsic_value": 685.2,
                "hyper_growth_warning": False,
                "is_bargain": False,
                "latest_quarter": "Mar " "2026",
                "market_cap": "10301",
                "moat_status": "Strong " "(Wide " "Moat)",
                "ncav_per_share": 65.0,
                "net_current_assets": 1479.0,
                "owner_earnings": 560.3,
                "pe_ratio": "13.0",
                "q_eps": "9.26",
                "q_net_profit": "211",
                "q_sales": "1450",
                "qoq_profit_growth": 5.5,
                "qoq_sales_growth": 1.3,
                "rd_pct": 1.5,
                "retained_earnings_ratio": 2.86,
                "roce": "23.5",
                "roe": "18.1",
                "valuation_alerts": [],
            },
            "target": "632.50",
            "target_high": "695.00",
            "target_low": "488.00",
            "target_median": "632.50",
            "ticker": "ZENSARTECH",
        },
    ],
    "textiles_apparel": [
        {
            "analyst_count": 10,
            "catalyst": "Major beneficiary of textile PLI, "
            "expanding home textiles capacity "
            "and global export market share.",
            "earnings_growth": "-22.1%",
            "growth_pct": "+18.7%",
            "name": "Welspun Living",
            "price": "138.54",
            "rating": "None",
            "rec_score": None,
            "revenue_growth": "-8.0%",
            "screener": {
                "book_value": "51.3",
                "capex": 487.0,
                "current_ratio": 1.5,
                "dividend_yield": "0.07",
                "graham_intrinsic_value": 102.4,
                "hyper_growth_warning": False,
                "is_bargain": False,
                "latest_quarter": "Mar 2026",
                "market_cap": "13288",
                "moat_status": "Weak/None",
                "ncav_per_share": 16.8,
                "net_current_assets": 1611.0,
                "owner_earnings": 122.2,
                "pe_ratio": "61.0",
                "q_eps": "1.08",
                "q_net_profit": "106",
                "q_sales": "2435",
                "qoq_profit_growth": 3433.3,
                "qoq_sales_growth": 7.6,
                "rd_pct": 1.5,
                "retained_earnings_ratio": 2.86,
                "roce": "6.25",
                "roe": "4.47",
                "valuation_alerts": [
                    "Fails " "Current " "Ratio " "(< " "2.0)",
                    "Fails " "Debt " "Limit " "(Debt " "> Net " "Assets)",
                    "Fails "
                    "P/E "
                    "Screen "
                    "(P/E "
                    "61.0 "
                    "> 15 "
                    "& "
                    "Price "
                    "> "
                    "Intrinsic)",
                    "Weak/No " "Economic " "Moat",
                ],
            },
            "target": "164.50",
            "target_high": "180.00",
            "target_low": "145.00",
            "target_median": "164.50",
            "ticker": "WELSPUNLIV",
        },
        {
            "analyst_count": 7,
            "catalyst": "Top apparel manufacturer, setting "
            "up new fabrics processing mill "
            "under textile PLI approval.",
            "earnings_growth": "-34.6%",
            "growth_pct": "+26.0%",
            "name": "Gokaldas Exports",
            "price": "674.50",
            "rating": "Strong Buy",
            "rec_score": 1.4,
            "revenue_growth": "+5.3%",
            "screener": {
                "book_value": "295",
                "capex": 213.8,
                "current_ratio": 2.29,
                "dividend_yield": "0.00",
                "graham_intrinsic_value": 528.3,
                "hyper_growth_warning": False,
                "is_bargain": False,
                "latest_quarter": "Mar 2026",
                "market_cap": "4942",
                "moat_status": "Weak/None",
                "ncav_per_share": 162.0,
                "net_current_assets": 1187.0,
                "owner_earnings": 32.0,
                "pe_ratio": "49.4",
                "q_eps": "4.91",
                "q_net_profit": "36",
                "q_sales": "1069",
                "qoq_profit_growth": 140.0,
                "qoq_sales_growth": 9.2,
                "rd_pct": 1.5,
                "retained_earnings_ratio": 2.86,
                "roce": "8.39",
                "roe": "4.72",
                "valuation_alerts": [
                    "Fails " "Debt " "Limit " "(Debt " "> Net " "Assets)",
                    "Fails "
                    "P/E "
                    "Screen "
                    "(P/E "
                    "49.4 "
                    "> 15 "
                    "& "
                    "Price "
                    "> "
                    "Intrinsic)",
                    "No " "Dividend " "Yield",
                    "Weak/No " "Economic " "Moat",
                ],
            },
            "target": "850.00",
            "target_high": "1100.00",
            "target_low": "799.00",
            "target_median": "850.00",
            "ticker": "GOKEX",
        },
        {
            "analyst_count": 7,
            "catalyst": "Leading denim manufacturer, "
            "investing in technical textiles "
            "under recent government schemes.",
            "earnings_growth": "+5.9%",
            "growth_pct": "+12.2%",
            "name": "Arvind Ltd",
            "price": "494.50",
            "rating": "Strong Buy",
            "rec_score": 1.0,
            "revenue_growth": "+15.0%",
            "screener": {
                "book_value": "154",
                "capex": 510.6,
                "current_ratio": 1.42,
                "dividend_yield": "0.76",
                "graham_intrinsic_value": 577.3,
                "hyper_growth_warning": False,
                "is_bargain": False,
                "latest_quarter": "Mar 2026",
                "market_cap": "12963",
                "moat_status": "Weak/None",
                "ncav_per_share": 50.4,
                "net_current_assets": 1320.0,
                "owner_earnings": 282.2,
                "pe_ratio": "30.4",
                "q_eps": "6.09",
                "q_net_profit": "165",
                "q_sales": "2553",
                "qoq_profit_growth": 63.4,
                "qoq_sales_growth": 7.6,
                "rd_pct": 1.5,
                "retained_earnings_ratio": 2.86,
                "roce": "13.8",
                "roe": "10.9",
                "valuation_alerts": [
                    "Fails " "Current " "Ratio " "(< " "2.0)",
                    "Fails " "Debt " "Limit " "(Debt " "> Net " "Assets)",
                    "Weak/No " "Economic " "Moat",
                ],
            },
            "target": "555.00",
            "target_high": "700.00",
            "target_low": "400.00",
            "target_median": "555.00",
            "ticker": "ARVIND",
        },
    ],
}

SECTOR_METADATA = {
    "aerospace_defence": {
        "desc": "Local aircraft assembly, BCD exemptions, " "and defense systems.",
        "icon": "✈️",
        "label": "Aerospace & Defence",
    },
    "big_cap_industries": {
        "desc": "Nation-building conglomerates, heavy "
        "engineering, and infrastructure giants.",
        "icon": "🏛️",
        "label": "Big Cap Industries",
    },
    "clean_energy": {
        "desc": "Solar, Wind, Green Hydrogen, and Grid " "Transmission initiatives.",
        "icon": "⚡",
        "label": "Clean Energy",
    },
    "cybersecurity": {
        "desc": "Data protection, software defense systems, "
        "and network security policies.",
        "icon": "🛡️",
        "label": "Cybersecurity",
    },
    "data_center_support": {
        "desc": "Power cooling, high-speed fiber "
        "cables, and server space "
        "infrastructure.",
        "icon": "🖥️",
        "label": "Data Center Support",
    },
    "fmcg": {
        "desc": "Rural disposable income, food processing, and "
        "consumer product growth.",
        "icon": "🛒",
        "label": "FMCG & Consumption",
    },
    "logistics_heavy_capital": {
        "desc": "Container manufacturing scheme, "
        "heavy machinery, and freight "
        "logistics.",
        "icon": "📦",
        "label": "Logistics & Capital Goods",
    },
    "macro_indicators": {
        "desc": "Passive index funds and ETFs tracking " "sector GVA growth.",
        "icon": "📊",
        "label": "Macro Indicators",
    },
    "manufacturing_electronics": {
        "desc": "PLI programs, semiconductor "
        "fabrications, and local contract "
        "assembly.",
        "icon": "🏭",
        "label": "Manufacturing & Electronics",
    },
    "semiconductors_equipment": {
        "desc": "India Semiconductor Mission (ISM) "
        "2.0, silicon fabs, and OSAT "
        "plants.",
        "icon": "💾",
        "label": "Semiconductors & Equipment",
    },
    "sports_athleisure": {
        "desc": "Active footwear, fitness apparel, and " "sports licensing brands.",
        "icon": "👟",
        "label": "Sports & Athleisure",
    },
    "surveillance_security": {
        "desc": "Smart City CCTVs, border security "
        "systems, and commercial surveillance "
        "cameras.",
        "icon": "📷",
        "label": "Surveillance & CCTV",
    },
    "textiles_apparel": {
        "desc": "Textile PLI programs, technical textiles, " "and global export hubs.",
        "icon": "👕",
        "label": "Textiles & Apparel",
    },
}

SECTOR_QUERIES = {
    "aerospace_defence": [
        'site:pib.gov.in "defence custom duty" OR ' '"defence aerospace"',
        "India defense manufacturing offset policies HAL " "BEL",
        '"Hindustan Aeronautics" OR "Bharat Electronics" '
        'OR "Astra Microwave" defence',
    ],
    "big_cap_industries": [
        'site:pib.gov.in "infrastructure" OR "capital ' 'expenditure" OR "Gati Shakti"',
        "India infra capex budget Larsen Toubro Reliance " "industries",
        "L&T order book Reliance green energy",
    ],
    "clean_energy": [
        'site:pib.gov.in "solar" OR "renewable" OR "green ' 'hydrogen"',
        "India clean energy policy ministry power",
        '"Adani Green" OR "Tata Power" OR "Suzlon" energy ' "order",
    ],
    "cybersecurity": [
        'site:pib.gov.in "cyber security" OR "cybersecurity" ' 'OR "CERT-In"',
        "India cyber security policy enterprise network " "protection",
        "TCS Quick Heal cyber contracts",
    ],
    "data_center_support": [
        'site:pib.gov.in "data center" OR "digital ' 'infrastructure"',
        "India data center policy expansion investments",
        '"Anant Raj" OR "Schneider" OR "Netweb" data ' "center",
    ],
    "fmcg": [
        'site:pib.gov.in "agriculture" OR "rural development" OR "food ' 'processing"',
        "India FMCG consumption rural demand inflation",
        "Varun Beverages ITC results shares",
    ],
    "logistics_heavy_capital": [
        'site:pib.gov.in "Container Scheme" OR ' '"heavy logistics"',
        "India container manufacturing capital " "goods railway capex",
        '"CONCOR" OR "BHEL" OR "Cummins" logistics ' "order",
    ],
    "macro_indicators": [
        'site:pib.gov.in "manufacturing GVA" OR ' '"industrial production"',
        "India manufacturing growth index PMI index",
        "Nifty India Manufacturing ETF shares",
    ],
    "manufacturing_electronics": [
        'site:pib.gov.in "PLI" electronics OR ' '"semiconductor" OR "OSAT"',
        "India electronics manufacturing PLI " "scheme semiconductor fab",
        "Dixon Kaynes semiconductor factory",
    ],
    "semiconductors_equipment": [
        'site:pib.gov.in "semiconductor PLI" OR ' '"ISM 2.0" OR "OSAT"',
        "India semiconductor fab equipment OSAT " "packaging plants",
        '"ASM Technologies" OR "RIR Power" OR ' '"SPEL" semiconductor',
    ],
    "sports_athleisure": [
        'site:pib.gov.in "sports" OR "Khelo India" OR ' '"footwear PLI"',
        "India sports brand athleisure market growth " "campus footwear",
        "Metro Brands Campus Activewear shares",
    ],
    "surveillance_security": [
        'site:pib.gov.in "CCTV" OR "safe city" OR ' '"surveillance"',
        "India smart city CCTV cameras border defense " "drones",
        '"CP Plus" OR "Aditya Infotech" OR "Allied '
        'Digital" OR "IdeaForge" surveillance',
    ],
    "textiles_apparel": [
        'site:pib.gov.in "textile PLI" OR "apparel ' 'manufacturing"',
        "India textiles export incentives technical " "textiles",
        '"Welspun" OR "Gokaldas" OR "Arvind" textiles',
    ],
}


def load_watchlist():
    watchlist_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "watchlist.json"
    )
    try:
        with open(watchlist_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        log.warning(
            "watchlist.json not found, using default STOCK_WATCHLIST dictionary."
        )
        return STOCK_WATCHLIST
    except json.JSONDecodeError:
        log.error(
            "Error decoding watchlist.json. Using default STOCK_WATCHLIST dictionary."
        )
        return STOCK_WATCHLIST
    except Exception as e:
        log.error(f"Unexpected error loading watchlist.json: {e}")
        return STOCK_WATCHLIST


def save_watchlist(watchlist):
    watchlist_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "watchlist.json"
    )
    try:
        from utils import atomic_write_json

        atomic_write_json(watchlist, watchlist_path)
        return True
    except OSError:
        return False
