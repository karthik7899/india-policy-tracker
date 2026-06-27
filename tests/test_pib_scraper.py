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
