import pytest
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
"""


def test_extract_row_values():
    soup = BeautifulSoup(MOCK_HTML, "html.parser")

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
