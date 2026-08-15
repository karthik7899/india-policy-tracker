"""Does NSE's announcements API answer a cloud runner? Measure, don't assume.

providers/nse_announcements.py is written to survive a refusal, but whether
it is the primary source or permanently the fallback depends on one fact we
cannot establish from the development sandbox (403 on CONNECT, the same
egress policy that blocks Screener, Yahoo and BSE). This asks from a runner.

It reports each layer separately, because they fail for different reasons and
a single pass/fail would hide which one moved:

  handshake   -> did the HTML site mint cookies, and which ones
  status      -> 200, or the 401/403 that means the IP or session is refused
  content-type-> application/json, or the HTML challenge page served with 200
  schema      -> the envelope shape, the record count, and the ACTUAL field
                 names, which is the part most likely to have drifted from
                 what the provider aliases

The field-name dump is deliberate. The provider reads through aliases so a
rename degrades one field instead of emptying the feed, and this is how we
learn a rename happened before it costs us a section.

Writes nothing. Never called by a briefing run.
"""

import datetime
import json
import sys

sys.path.insert(0, __file__.rsplit("/", 2)[0])

from providers import nse_announcements as nse  # noqa: E402


def probe():
    session = nse.build_session()
    try:
        print("=== HANDSHAKE")
        ok = nse.handshake(session)
        cookies = sorted(session.cookies.keys()) if session.cookies else []
        print(f"    cookies harvested: {ok} -> {cookies}")
        if not ok:
            print("    the edge served a challenge page; the API call will be refused")

        today = datetime.date.today()
        params = {
            "index": nse.DEFAULT_INDEX,
            "from_date": today.strftime("%d-%m-%Y"),
            "to_date": today.strftime("%d-%m-%Y"),
        }
        print(f"\n=== API {nse.API_URL}")
        print(f"    params: {params}")

        response = session.get(
            nse.API_URL,
            params=params,
            headers=nse.API_HEADERS,
            timeout=nse.REQUEST_TIMEOUT_S,
        )
        content_type = response.headers.get("Content-Type", "<none>")
        body = response.text or ""
        print(f"    status      : {response.status_code}")
        print(f"    content-type: {content_type}")
        print(f"    bytes       : {len(body)}")

        if "application/json" not in content_type.lower():
            # Short bodies print verbatim: an earlier probe of BSE described an
            # 18-byte response by its keys alone and hid the answer.
            print(f"    body        : {body[:600]!r}")
            print("\n    VERDICT: refused — HTML where JSON was asked for.")
            return

        try:
            payload = json.loads(body)
        except ValueError as e:
            print(f"    body        : {body[:600]!r}")
            print(f"\n    VERDICT: JSON declared but undecodable: {e}")
            return

        if isinstance(payload, dict):
            print(f"    envelope    : dict, keys {sorted(payload.keys())[:12]}")
            rows = payload.get("data", payload.get("rows", []))
        else:
            print(f"    envelope    : {type(payload).__name__}")
            rows = payload

        print(f"    records     : {len(rows) if isinstance(rows, list) else 'n/a'}")
        if isinstance(rows, list) and rows:
            print(f"\n    FIELD NAMES : {sorted(rows[0].keys())}")
            print("\n    FIRST RECORD:")
            print(f"    {json.dumps(rows[0], indent=6)[:1200]}")

            # What the provider would actually produce from it — the end-to-end
            # answer, not just that bytes arrived.
            normalized = nse.normalize(rows[0])
            print(f"\n    NORMALIZED  : {normalized}")
            missing = [k for k, v in (normalized or {}).items() if not v]
            if missing:
                print(f"    EMPTY FIELDS: {missing} — check the aliases")
            print("\n    VERDICT: reachable. NSE can serve as the primary source.")
        else:
            print(
                "\n    VERDICT: reachable but empty. Before concluding the "
                "endpoint is wrong, check this is a trading day and that "
                "announcements have been published yet today."
            )
    finally:
        session.close()


if __name__ == "__main__":
    try:
        probe()
    except Exception as e:  # noqa: BLE001 - a probe reports, it does not crash
        print(f"    PROBE FAILED: {type(e).__name__}: {e}")
    sys.exit(0)
