# What the upstreams actually serve

Every host this pipeline reads is denied by the development sandbox (403 on
CONNECT), so nothing here could be established locally. Each entry was
measured from a GitHub Actions runner, and each carries the date it was
measured, because these are undocumented endpoints and the exchanges move
them.

**Newest first**, for the same reason `.jules/bolt.md` is: a correction is
always written after the thing it corrects, so newest-first guarantees a
retraction is read before the advice it overturns.

Findings are kept here rather than in the scripts that produced them. A probe
whose question is settled is a 400-line file that can never run again; the
answer is worth keeping, the code is not. Where a script still runs, it is
named.

---

## NSE's announcements API answers a runner — it is the primary source

**Measured 2026-09-14**, run 34806776390
(`probe_upstream.py --source nse-announcements`).

`providers/nse_announcements.py` is written to survive a refusal, which means
the pipeline cannot tell you which of the two lives it is leading. It is the
primary filings source, not the fallback.

```
handshake   : True -> cookies ['AKA_A2', '_abck', 'bm_sz']
url         : https://www.nseindia.com/api/corporate-announcements
params      : index=equities, from_date=14-09-2026, to_date=14-09-2026
status      : 200
content-type: application/json; charset=utf-8
bytes       : 6727      envelope: list      records: 9
```

The Akamai bot-manager cookies are the same three measured on 14 Aug 2026, so
the handshake route is stable. Nine records against that date's 44,674 bytes
is a time-of-day difference, not a decline — this ran at 10:08 IST, minutes
into the session.

**The envelope arrived as a bare list, not the `{"data": [...]}` dict.** In
most shapes of code that is a silent empty feed. Here it is not:
`exchange_api.rows_from` accepts either, and says why — NSE has served both
for this same endpoint. The alias layer held too: `normalize()` reported no
empty fields, so none of the twenty keys (`an_dt`, `attchmntText`, `sm_name`,
`smIndustry`, `symbol`, …) has drifted.

Re-measure rather than trust this: it is an undocumented endpoint behind a
bot manager, and both of those move.

---

## Screener serves no promoter pledge row — for anybody

**Measured 2026-09-10** (`scripts/probe_screener_pledge.py`, run 6 — script
since removed, this is its record).

`analysis/pledging.py` had been complete and correct for months and had never
graded a single holding: *"0 alert(s) from 0 holding(s) with a disclosed
pledge; 70 not disclosed or not parsed."*

Six holdings were checked, chosen so that a null result would mean something:
HAL as a government-owned control that structurally **cannot** carry a
promoter pledge, plus SUZLON, ANANTRAJ, OPTIEMUS, ADSL and FAZE3Q — all
promoter-led, several smallcap. Every one carried the same rows (Promoters,
FIIs, DIIs, Public, sometimes Government/Others). **None carried a pledge
row.**

The expander behind `Promoters +` was chased to its endpoint,
`/api/3/{companyId}/investors/{classification}/{period}/`, which answers 200
unauthenticated and returns per-shareholder **holdings** — names and their
quarterly percentages — not pledge.

### The reading error this cost, which is the more useful half

The first conclusion drawn here was that "Screener has no pledge row," from a
once-per-run diagnostic that happened to fire on **HAL**. HAL is a PSU. Its
missing pledge row is *correct output* and says nothing whatsoever about the
other 69 holdings. That was a generalisation from n=1, on the least
informative sample the watchlist contains.

The conclusion survived re-testing, but it was not earned at the time. A
once-per-run diagnostic does not get to choose a representative sample, and
its output must never be read as one.

**Consequence:** `providers/screener.py` keeps the lookup as a cheap tripwire
in case Screener starts publishing the row, worded "not served" rather than
"not matched" so the next reader is not sent after a regex that was never the
problem. `analysis/pledging.py` cannot be fed from Screener and needs the
exchanges' shareholding-pattern filings to do anything at all. **Still open.**

---

## BSE refuses headless browsers, and this approach is dead

**Measured 2026-08, run 5** (`scripts/probe_bse_network.py` — script since
removed, this is its record).

The intent was to read what BSE's own pages call, rather than keep guessing
endpoint names — guessing had failed eight times across two runs. All five
pages returned:

```
landed: HTTP 403 | <the url asked for>
title : 'Access Denied'
dom   : ~250 chars, 0 tables, 0 rows
head  : "Access Denied You don't have permission to access ...
         https://errors.edgesuite.net/"
all hosts: {'www.bseindia.com': 1}
```

One response per page and no JS ever ran, so there was no XHR to capture: the
browser never received a page at all.

**The load-bearing comparison:** the endpoint probe runs on the *same runner*
and is served normally — plain `requests` carrying the UA and Referer from
`providers/isin_master.py` pulled 851 KB of bhavcopy and 1.75 MB of scrip
master from these hosts. So the filter is on **browser fingerprint**, not on
the UA string and not on the IP. A spoofed user agent and
`--disable-blink-features=AutomationControlled` changed nothing.

**Do not try to defeat this.** It would mean fingerprint-spoofing tooling —
evasion of a control the site is plainly asserting — and it would be a fragile
thing to hang a daily briefing on besides. The shareholding and announcement
gaps stay open, to be closed from a source that will have us.

### The diagnostic lesson

Run 4 reported "no API calls captured" with no navigation error, which could
not be told apart from its own filter never matching. **The 403 was
invisible.** Any probe must distinguish "the page fired nothing" from "my
filter matched nothing" before drawing a conclusion — print the landing URL,
title, HTTP status and a DOM fingerprint, and count every response by host.

---

## The BSE announcements path was wrong, not the parameters

**Measured 2026-08** (`scripts/probe_bse_announcements.py` — script since
removed; the finding is live in `providers/bse_announcements.py`).

Thirty-two attempts across endpoint names, parameter names and values, date
formats, cookies, Referer host and path, and Origin. All returned
`No Record Found!` from `BseIndiaAPI/api/AnnGetData/w`.

The search ended when the real request was captured from Chrome's Network tab
on the live announcements page:

```
https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w
  ?pageno=1&strCat=-1&strPrevDate=20260815&strScrip=&strSearch=P
  &strToDate=20260815&strType=C&subcategory=-1
```

**The parameters were right the whole time. The path was wrong** — and it was
an assumption rather than a measurement. DevTools' Name column shows only the
last segment, and every BSE endpoint ends in `/w`, so `AnnGetData` and
`AnnSubCategoryGetData` are indistinguishable in that list.

`AnnGetData` is a real endpoint that answers this exact query with a polite
empty result, which is the most expensive kind of wrong: it looks like a data
problem for as long as you care to look.

---

## BSE endpoint catalogue

**Measured 2026-08-14** — and **stale**. Re-run
`scripts/probe_bse.py` (workflow: `probe-bse.yml`) before trusting any of it.
That script is a deliberate sweep across many endpoints, which is why it is
kept separate from `scripts/probe_upstream.py`, whose rule is one request per
source.

The bhavcopy and scrip master are the two that work and that the pipeline
depends on; see the script's own `WORKS` list for the measured shapes.

---

## The BSE/NSE ticker namespace collision, counted

**Measured 2026-09-14** (`scripts/probe_upstream.py --source bse-scrips`).

NSE's `SYMBOL` and BSE's `scrip_id` are ticker-like codes in **different
namespaces**, and nothing guarantees a BSE-only scrip_id is not also some
other company's NSE symbol. The merge already refuses to overwrite, so a
collision cannot corrupt a mapping we trust — but "cannot corrupt" is not the
same as "is fine", and until it was counted the risk was an assumption.

It is now counted. Of 5,002 parsed BSE mappings, **4** disagree with the
master, and all four are genuinely different issuers:

```
CREATIVE  INE985W01018 -> INE146E01015
FOCUS     INE593W01028 -> INE0DXR01010
KALYANI   INE610E01010 -> INE0N6U01018
WORTH     INE196Y01018 -> INE114O01020
```

None is a watchlist holding. The never-overwrite policy is doing exactly the
job it was written for, and needs no rethinking.

---

## ISINs change, and the master was stale

**Measured 2026-09-13**, run 161.

The module's founding premise — that a symbol's ISIN is stable — was false.
An ISIN is `IN` + `E` + a 7-character issuer code + a 2-digit issue series +
a check digit, and a corporate action (a split, a face-value change) mints a
**new issue series for the same issuer**. Same issuer plus higher series is
therefore a corporate action, not a different company.

Letting NSE correct its own namespace wrote 140 changes, every one
same-issuer/higher-series. Six live holdings (ADANIPOWER, COFORGE, DIACABS,
PERSISTENT, PGIL, VBL) had been carrying pre-split identity.

As of 2026-09-14 the master and NSE agree on all 2,568 symbols, with none
absent.
