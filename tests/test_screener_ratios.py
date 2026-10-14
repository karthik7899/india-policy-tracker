"""Working-capital measures from Screener's ratios table (providers/screener.py).

The rows are the ones Screener served for HAL and BEL on 14 Oct 2026; a
bank's table (HDFCBANK) had only ROE (docs/upstream-findings.md).
"""

from providers.screener import parse_company_page

RATIOS = (
    '<section id="ratios"><table><tbody>'
    "<tr><td>Debtor Days</td><td>110</td><td>98</td><td>72</td></tr>"
    "<tr><td>Inventory Days</td><td>600</td><td>580</td><td>540</td></tr>"
    "<tr><td>Days Payable</td><td>90</td><td>85</td><td>80</td></tr>"
    "<tr><td>Cash Conversion Cycle</td><td>620</td><td>593</td><td>532</td></tr>"
    "<tr><td>Working Capital Days</td><td>-40</td><td>-75</td><td>-110</td></tr>"
    "<tr><td>ROCE %</td><td>28%</td><td>30%</td><td>32%</td></tr>"
    "</tbody></table></section>"
)
BANK_RATIOS = (
    '<section id="ratios"><table><tbody>'
    "<tr><td>ROE %</td><td>16%</td><td>14%</td></tr>"
    "</tbody></table></section>"
)


def test_the_latest_working_capital_and_debtor_days_are_read():
    sc, _w = parse_company_page(f"<html><body>{RATIOS}</body></html>", "HAL", "x")
    # The latest year's; negative working-capital days (advances from
    # customers) are kept as they are.
    assert sc["debtor_days"] == 72.0 and sc["working_capital_days"] == -110.0
    assert sc["roce_trend"][-1] == 32.0


def test_a_lenders_ratios_table_has_neither():
    sc, _w = parse_company_page(
        f"<html><body>{BANK_RATIOS}</body></html>", "HDFCBANK", "x"
    )
    assert "debtor_days" not in sc and "working_capital_days" not in sc
