"""Ask one upstream source what it is actually serving, and say so.

Every upstream this pipeline depends on is denied by the development
environment's egress policy, so a question like "what does Screener's peers
endpoint return now?" cannot be answered locally. Twice this week it was
answered the slow way instead: change the code to log more, merge it, fire the
daily brief, read the log, repeat. Three round trips for the peer radar, and
six briefing emails sent to a human who did not ask for them.

This is the fast way. It runs in CI, where the hosts ARE reachable, and it:

  * makes ONE request per source, never a sweep;
  * feeds the response to the REAL parser, because a probe with its own
    parsing proves nothing about the pipeline — the peer-table bug was a
    parser bug, not a fetch bug;
  * prints a bounded description of what came back, and saves the raw sample
    as a workflow artifact so a fixture can be built from the genuine article
    rather than reconstructed by hand;
  * sends no email, writes no payload, commits nothing.

    python scripts/probe_upstream.py --source screener-peers --symbol HAL
    python scripts/probe_upstream.py --source all
"""

import argparse
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

OUT_DIR = os.environ.get("PROBE_OUT", "probe-output")

# Samples are for building fixtures, not for archiving a website. Enough to
# see the shape of a response and no more.
SAMPLE_BYTES = 40000
SHOW_CHARS = 400


def _save(name, text):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(str(text)[:SAMPLE_BYTES])
    return path


def _report(title, status, content_type, body, parsed_summary, saved):
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")
    print(f"  HTTP        : {status}")
    print(f"  Content-Type: {content_type or 'unstated'}")
    print(f"  Size        : {len(body or '')} bytes")
    print(f"  PARSED      : {parsed_summary}")
    if saved:
        print(f"  Sample      : {saved}")
    visible = " ".join(str(body or "").split())[:SHOW_CHARS]
    print(f"  First {SHOW_CHARS} chars:\n    {visible}")


async def probe_screener_peers(symbol):
    """The endpoint that returned a readable table nobody could read."""
    import aiohttp

    from providers.screener import fetch_screener_async, parse_peer_table

    async with aiohttp.ClientSession() as session:
        # The company page first, because the peers URL needs its warehouse id
        # — and that dependency is itself worth exercising.
        _t, sc, warehouse_id = await fetch_screener_async(session, symbol, "probe", 0.0)
        print(
            f"  company page: screener fields={len(sc or {})} "
            f"warehouse_id={warehouse_id!r}"
        )
        if not warehouse_id:
            print("  PARSED      : no warehouse id, so the peers URL cannot be built")
            return False

        url = f"https://www.screener.in/api/company/{warehouse_id}/peers/"
        async with session.get(
            url, headers={"X-Requested-With": "XMLHttpRequest"}, timeout=15
        ) as response:
            body = await response.text()
            status = response.status
            ctype = response.headers.get("Content-Type", "")

    rows = parse_peer_table(body)
    summary = f"{len(rows)} peer row(s)"
    if rows:
        summary += f"; first = {json.dumps(rows[0])[:160]}"
    _report(
        f"SCREENER PEERS ({symbol}, warehouse {warehouse_id})",
        status,
        ctype,
        body,
        summary,
        _save("screener_peers.html", body),
    )
    return status == 200 and bool(rows)


async def probe_nse_isin():
    """EQUITY_L.csv — the source that settles an ISIN disagreement."""
    import aiohttp

    from providers.isin_master import (
        _HEADERS,
        _NSE_EQUITY_LIST_URL,
        load_isin_master,
        parse_equity_csv,
    )

    async with aiohttp.ClientSession() as session:
        async with session.get(
            _NSE_EQUITY_LIST_URL, headers=_HEADERS, timeout=20, allow_redirects=False
        ) as response:
            body = await response.text()
            status, ctype = response.status, response.headers.get("Content-Type", "")

    live = parse_equity_csv(body)
    master = load_isin_master()
    disagree = {
        s: (master[s], i) for s, i in live.items() if s in master and master[s] != i
    }
    missing = [s for s in live if s not in master]

    summary = (
        f"{len(live)} symbol(s) parsed; {len(missing)} absent from the master; "
        f"{len(disagree)} disagree"
    )
    _report(
        "NSE EQUITY_L.csv", status, ctype, body, summary, _save("nse_equity.csv", body)
    )

    if disagree:
        print(
            f"\n  DISAGREEMENTS ({len(disagree)}) — the question a log cannot answer:"
        )
        same_issuer = sum(1 for o, n in disagree.values() if o[:9] == n[:9])
        print(
            f"    same issuer, different issue series (a corporate action): {same_issuer}"
        )
        print(
            f"    genuinely different issuer (a real collision):           "
            f"{len(disagree) - same_issuer}"
        )
        for sym, (old, new) in sorted(disagree.items())[:15]:
            kind = "series" if old[:9] == new[:9] else "ISSUER"
            print(f"      {sym:14} {old} -> {new}   [{kind}]")
    return bool(live)


def probe_bse_scrips():
    """BSE's scrip master — the other half of the ISIN namespace question."""
    from providers.bse_announcements import fetch_scrip_master
    from providers.isin_master import load_isin_master, parse_bse_scrip_rows

    rows = fetch_scrip_master()
    mapping = parse_bse_scrip_rows(rows)
    master = load_isin_master()
    disagree = {
        s: (master[s], i) for s, i in mapping.items() if s in master and master[s] != i
    }

    print(f"\n{'=' * 72}\nBSE SCRIP MASTER\n{'=' * 72}")
    print(f"  rows returned : {len(rows or [])}")
    print(f"  parsed        : {len(mapping)} scrip_id -> ISIN")
    print(f"  disagree with the master: {len(disagree)}")
    if rows:
        _save("bse_scrips_sample.json", json.dumps(rows[:50], indent=2))
        print(f"  Sample        : {OUT_DIR}/bse_scrips_sample.json")
    if disagree:
        same_issuer = sum(1 for o, n in disagree.values() if o[:9] == n[:9])
        print(f"    same issuer (corporate action): {same_issuer}")
        print(f"    different issuer (collision)  : {len(disagree) - same_issuer}")
        for sym, (old, new) in sorted(disagree.items())[:15]:
            kind = "series" if old[:9] == new[:9] else "ISSUER"
            print(f"      {sym:14} {old} -> {new}   [{kind}]")
    return bool(mapping)


async def probe_nse_delivery():
    import aiohttp

    from providers.nse_delivery import fetch_delivery_async

    async with aiohttp.ClientSession() as session:
        delivery = await fetch_delivery_async(session)
    print(f"\n{'=' * 72}\nNSE DELIVERY BHAVCOPY\n{'=' * 72}")
    print(f"  securities parsed: {len(delivery or {})}")
    if delivery:
        sym = next(iter(delivery))
        print(f"  sample           : {sym} -> {json.dumps(delivery[sym])[:200]}")
    return bool(delivery)


def probe_nse_announcements():
    """Is NSE's disclosure API the primary filings source, or the fallback?

    providers/nse_announcements.py is written to survive a refusal, so the
    pipeline cannot tell you which of the two it is currently living as. Only
    a runner can.

    Each layer is reported separately because they fail for different reasons
    and a single pass/fail would hide which one moved: the handshake mints
    cookies or does not; the API answers 200 or the 401/403 that means the IP
    is refused; the body is JSON or the challenge page served WITH a 200; and
    the field names are the part most likely to have quietly drifted. The
    provider reads through aliases so a rename degrades one field rather than
    emptying the feed, which is exactly why a rename would otherwise go
    unnoticed until it cost a section.
    """
    import datetime

    from providers import nse_announcements as nse
    from providers.screener import describe_fragment

    print(f"\n{'=' * 72}\nNSE CORPORATE ANNOUNCEMENTS\n{'=' * 72}")
    session = nse.build_session()
    try:
        ok = nse.handshake(session)
        cookies = sorted(session.cookies.keys()) if session.cookies else []
        print(f"  handshake   : {ok} -> cookies {cookies}")
        if not ok:
            # Deliberately does NOT name a cause. handshake() swallows its
            # exception and returns a bare False, which covers two different
            # worlds: the edge answered and challenged us, or the request
            # never reached the edge at all. This line used to assert the
            # first, and said so on a run where the agent proxy had refused
            # the CONNECT — blaming NSE for a local egress policy. The log
            # line immediately above carries the real reason; read it.
            print(
                "  no cookies minted, so the API call will be refused. Cause "
                "is NOT established here — the WARNING above says whether the "
                "edge challenged us or the request never left this machine."
            )

        today = datetime.date.today()
        params = {
            "index": nse.DEFAULT_INDEX,
            "from_date": today.strftime("%d-%m-%Y"),
            "to_date": today.strftime("%d-%m-%Y"),
        }
        response = session.get(
            nse.API_URL,
            params=params,
            headers=nse.API_HEADERS,
            timeout=nse.REQUEST_TIMEOUT_S,
        )
        ctype = response.headers.get("Content-Type", "")
        body = response.text or ""
        print(f"  url         : {nse.API_URL}")
        print(f"  params      : {params}")
        print(f"  status      : {response.status_code}")
        print(f"  content-type: {ctype or 'unstated'}")
        print(f"  bytes       : {len(body)}")

        if "application/json" not in ctype.lower():
            # Short bodies print verbatim. An earlier BSE probe described an
            # 18-byte response by its keys alone and hid the answer in doing so.
            print(f"  body        : {describe_fragment(body, ctype)}")
            print("  VERDICT     : refused — HTML where JSON was asked for.")
            return False

        try:
            payload = json.loads(body)
        except ValueError as e:
            print(f"  body        : {describe_fragment(body, ctype)}")
            print(f"  VERDICT     : JSON declared but undecodable: {e}")
            return False

        if isinstance(payload, dict):
            print(f"  envelope    : dict, keys {sorted(payload.keys())[:12]}")
            rows = payload.get("data", payload.get("rows", []))
        else:
            print(f"  envelope    : {type(payload).__name__}")
            rows = payload

        count = len(rows) if isinstance(rows, list) else 0
        print(f"  records     : {count}")
        _save("nse_announcements.json", body)
        print(f"  Sample      : {OUT_DIR}/nse_announcements.json")

        if not (isinstance(rows, list) and rows):
            # Empty is not the same as refused, and saying so matters: on a
            # holiday or before the day's first filing this is correct output.
            print(
                "  VERDICT     : reachable but empty. Before concluding the "
                "endpoint moved, check this is a trading day and that "
                "announcements have been published yet today."
            )
            return False

        print(f"  FIELD NAMES : {sorted(rows[0].keys())}")
        normalized = nse.normalize(rows[0])
        print(f"  NORMALIZED  : {json.dumps(normalized, default=str)[:300]}")
        empty = [k for k, v in (normalized or {}).items() if not v]
        if empty:
            print(f"  EMPTY FIELDS: {empty} — check the aliases")
        print("  VERDICT     : reachable. NSE can serve as the primary source.")
        return True
    finally:
        session.close()


SOURCES = {
    "screener-peers": ("async", probe_screener_peers),
    "nse-isin": ("async-noarg", probe_nse_isin),
    "bse-scrips": ("sync", probe_bse_scrips),
    "nse-delivery": ("async-noarg", probe_nse_delivery),
    "nse-announcements": ("sync", probe_nse_announcements),
}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", default="all", choices=[*SOURCES, "all"])
    ap.add_argument("--symbol", default="HAL", help="for the per-company probes")
    args = ap.parse_args()

    chosen = list(SOURCES) if args.source == "all" else [args.source]

    # "Did not raise" is not "answered". Every probe reports whether it came
    # back with data anyone could use, because a summary that counts absence
    # of exceptions is the exact failure this tool was built to stop: the
    # first version of this line said "4/4 source(s) answered" on a run where
    # all four were blocked at the proxy.
    results = {}
    for name in chosen:
        kind, fn = SOURCES[name]
        try:
            if kind == "async":
                results[name] = bool(asyncio.run(fn(args.symbol)))
            elif kind == "async-noarg":
                results[name] = bool(asyncio.run(fn()))
            else:
                results[name] = bool(fn())
        except Exception as e:  # noqa: BLE001 - one dead source must not hide the rest
            results[name] = False
            print(f"\n{'=' * 72}\n{name.upper()}\n{'=' * 72}")
            print(f"  FAILED: {type(e).__name__}: {str(e)[:300]}")

    usable = [n for n, ok in results.items() if ok]
    print(f"\n{'=' * 72}\nSUMMARY\n{'=' * 72}")
    for name, ok in results.items():
        print(f"  {'DATA  ' if ok else 'NOTHING'} {name}")
    print(f"\n{len(usable)}/{len(chosen)} source(s) returned usable data.")
    if not usable:
        print(
            "  Every source came back empty. From a development sandbox that is\n"
            "  normally the egress policy rather than the upstream — the proxy\n"
            "  says so in the body ('Host not in allowlist'). From CI it means\n"
            "  the sources really are down or have changed."
        )
    # Always exit 0: a blocked or changed upstream is a FINDING, and failing
    # the job would make the tool feel broken when it is doing its job.
    return 0


if __name__ == "__main__":
    sys.exit(main())
