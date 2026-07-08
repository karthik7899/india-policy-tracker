import urllib.parse
from logger import log


async def resolve_ticker_from_name_async(company_name, session):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={urllib.parse.quote(company_name)}&quotesCount=5"
    try:
        async with session.get(url, headers=headers, timeout=10) as response:
            if response.status == 200:
                data = await response.json()
                quotes = data.get("quotes", [])
                for q in quotes:
                    symbol = q.get("symbol", "")
                    if symbol.endswith(".NS"):
                        return (
                            symbol.split(".")[0],
                            q.get("longname") or q.get("shortname") or company_name,
                        )
                for q in quotes:
                    symbol = q.get("symbol", "")
                    if symbol.endswith(".BO"):
                        return (
                            symbol.split(".")[0],
                            q.get("longname") or q.get("shortname") or company_name,
                        )
    except Exception as e:
        log.error(f"Error resolving ticker for {company_name}: {e}")
    return None, None


def resolve_ticker_from_name(company_name, session=None):
    import requests

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={urllib.parse.quote(company_name)}&quotesCount=5"
    try:
        if session:
            r = session.get(url, headers=headers, timeout=10)
        else:
            r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            quotes = data.get("quotes", [])
            for q in quotes:
                symbol = q.get("symbol", "")
                if symbol.endswith(".NS"):
                    return (
                        symbol.split(".")[0],
                        q.get("longname") or q.get("shortname") or company_name,
                    )
            for q in quotes:
                symbol = q.get("symbol", "")
                if symbol.endswith(".BO"):
                    return (
                        symbol.split(".")[0],
                        q.get("longname") or q.get("shortname") or company_name,
                    )
    except Exception as e:
        log.error(f"Error resolving ticker for {company_name}: {e}")
    return None, None


def extract_row_values(soup, section_id, row_label_pattern):
    sec = soup.find("section", id=section_id)
    if not sec:
        return []
    import re

    td_label = sec.find("td", string=re.compile(row_label_pattern))
    if td_label:
        tr = td_label.find_parent("tr")
        if tr:
            tds = tr.find_all("td")
            vals = [
                td.get_text(strip=True).replace(",", "").replace("%", "")
                for td in tds[1:]
                if td.get_text(strip=True)
            ]
            numeric_vals = []
            for v in vals:
                try:
                    numeric_vals.append(float(v))
                except ValueError:
                    pass
            return numeric_vals
    return []


def calculate_trend(values, periods=4):
    if not values:
        return [0] * periods
    return values[-periods:]


def calculate_growth(val1, val2):
    if not val1 or val1 == 0:
        return 0.0
    return round(((val2 - val1) / abs(val1)) * 100, 2)
