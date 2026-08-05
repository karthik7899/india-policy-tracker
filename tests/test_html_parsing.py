from bs4 import BeautifulSoup
from analysis.parsing import extract_row_values, calculate_trend, calculate_growth

MOCK_HTML = """
<section id="quarters">
    <table>
        <tbody>
            <tr>
                <td>Sales</td>
                <td>1,000</td>
                <td>1,200.5</td>
                <td>1,150.0</td>
                <td>1,500</td>
            </tr>
            <tr>
                <td>OPM %</td>
                <td>10%</td>
                <td>12%</td>
                <td>-5%</td>
                <td>15%</td>
            </tr>
        </tbody>
    </table>
</section>
<section id="balance-sheet">
    <table>
        <tbody>
            <tr>
                <td>Borrowings</td>
                <td>500</td>
                <td>400</td>
                <td>300</td>
                <td>0</td>
            </tr>
        </tbody>
    </table>
</section>
<section id="profit-loss">
    <table>
        <tbody>
            <tr>
                <td><button class="button-plain">Sales</button></td>
                <td>1,000</td>
                <td>1,200</td>
                <td>1,450</td>
                <td>1,700</td>
            </tr>
            <tr>
                <td>EPS in Rs</td>
                <td>10.0</td>
                <td>12.5</td>
                <td>15.0</td>
                <td>18.0</td>
            </tr>
        </tbody>
    </table>
</section>
"""


def test_extract_row_values():
    soup = BeautifulSoup(MOCK_HTML, "lxml")

    # Test normal extraction with commas
    sales = extract_row_values(soup, "quarters", "Sales")
    assert sales == [1000.0, 1200.5, 1150.0, 1500.0]

    # Test percentage extraction with negatives
    opm = extract_row_values(soup, "quarters", "OPM")
    assert opm == [10.0, 12.0, -5.0, 15.0]

    # Test missing section
    missing_sec = extract_row_values(soup, "invalid", "Sales")
    assert missing_sec == []

    # Test missing row
    missing_row = extract_row_values(soup, "quarters", "R&D")
    assert missing_row == []


def test_extract_annual_profit_loss_rows():
    """The annual P&L rows feed multi-year CAGR and trailing earnings.

    Screener wraps expandable row labels in a <button>, which is what silently
    blanked these extractions before the row matcher was repaired — so the
    fixture keeps that markup on the Sales row.
    """
    soup = BeautifulSoup(MOCK_HTML, "lxml")
    assert extract_row_values(soup, "profit-loss", "Sales") == [
        1000.0,
        1200.0,
        1450.0,
        1700.0,
    ]
    assert extract_row_values(soup, "profit-loss", "EPS") == [10.0, 12.5, 15.0, 18.0]


def test_calculate_trend():
    assert calculate_trend([1, 2, 3, 4, 5], 3) == [3, 4, 5]
    assert calculate_trend([10], 4) == [10]
    assert calculate_trend([], 2) == [0, 0]


def test_calculate_growth():
    assert calculate_growth(100, 150) == 50.0
    assert calculate_growth(200, 100) == -50.0
    assert calculate_growth(-100, -50) == 50.0
    assert calculate_growth(0, 100) == 0.0
    assert calculate_growth(None, 100) == 0.0


class TestParserRecovery:
    """Why the scrapers pass "lxml" rather than "html.parser".

    Nine bot-authored pull requests proposed this swap as a speed
    optimisation. The measurable benefit is correctness: on the malformed
    markup real scraped pages contain, html.parser mis-recovers in ways that
    produce numbers no cell ever held, with no error raised.
    """

    def _both(self, html, section="quarters", label="Sales"):
        return (
            extract_row_values(BeautifulSoup(html, "html.parser"), section, label),
            extract_row_values(BeautifulSoup(html, "lxml"), section, label),
        )

    def test_unclosed_cells_are_not_fused_into_one_number(self):
        """html.parser reads 100 and 200 as a single value of 100200."""
        html = (
            "<section id='quarters'><table><tbody>"
            "<tr><td>Sales<td>100<td>200"
            "</tbody></table></section>"
        )
        legacy, lxml_values = self._both(html)
        assert lxml_values == [100.0, 200.0]
        assert 100200.0 in legacy  # the defect this parser choice avoids

    def test_an_unclosed_row_does_not_absorb_the_next_one(self):
        """Expenses bled into Sales, making the series two rows long."""
        html = (
            "<section id='quarters'><table><tbody>"
            "<tr><td>Sales</td><td>100</td><td>200</td>"
            "<tr><td>Expenses</td><td>50</td><td>60</td>"
            "</tbody></table></section>"
        )
        legacy, lxml_values = self._both(html)
        assert lxml_values == [100.0, 200.0]
        assert legacy == [100.0, 200.0, 50.0, 60.0]

    def test_well_formed_markup_parses_identically(self):
        """The swap must not move any number on pages that are already valid."""
        for section, label in (
            ("quarters", "Sales"),
            ("balance-sheet", "Borrowings"),
        ):
            legacy, lxml_values = self._both(MOCK_HTML, section, label)
            assert legacy == lxml_values

    def test_the_nested_button_label_still_resolves(self):
        """Screener wraps expandable row labels in a <button>; that quirk
        already cost every sales/debt metric once."""
        html = (
            "<section id='quarters'><table><tbody>"
            "<tr><td><button class='button-plain'>Sales<span></span></button></td>"
            "<td>100</td><td>200</td></tr>"
            "</tbody></table></section>"
        )
        legacy, lxml_values = self._both(html)
        assert lxml_values == [100.0, 200.0] == legacy
