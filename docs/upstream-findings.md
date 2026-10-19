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

## Google News never links to PIB; PIB's own list of a month's releases does

**Measured 2026-10-19**, runs 39235376433, 39259347814, 39264070803 and
39265315717 (`probe_upstream.py --source pib-pli`, which now runs the
scraper's own path a step at a time).

**Google News** answers the PLI search (30 results for 30 days), but its links
lead to Google's own page: HTTP 200, 584 KB, titled "Google News", never naming
pib.gov.in. The scraper took that page for the release and found no names in
it; the daily log said "5 link(s) led to a page that was not the release".

**PIB's RSS feed** is no way round it. `RssMain.aspx?ModId=6&Lang=1&Regid=3`
redirects to `Lang=2&reg=48`, the Hindi feed, whatever the address asks for,
and holds 20 releases: a few hours of PIB's day.

**`allRel.aspx?reg=3&lang=1`**, PIB Delhi's list in English, is an ASP.NET form.
A GET is today's list. The form posted back with `ddlday`, `ddlMonth` and
`ddlYear` set and `__EVENTTARGET=ctl00$ContentPlaceHolder1$ddlday`, as its day
menu does, is that day's list: 77 releases for 25 September, each linked as
`/PressReleaseDetail.aspx?PRID=N`. Use the www host; the bare one redirects.

**A whole month is one request.** With the day menu at its first option, "All"
(value `0`), the same post lists the month: 953 releases for October to the
19th (958 KB), 1,429 for September (1.3 MB). That matters because Google's
dates are when Google saw a page, not when PIB posted it: "India's GDP
Performance", dated 17 October by Google, is PRID 2305422 from early September,
and the ECMS release Google dated 15 October is on September's list. Day lists
asked for Google's day and the day before found one story in twenty; the two
months' lists found six. Most of the rest are PIB backgrounders ("India's
Drone Ecosystem"), which are not on the list of releases at all, and a
backgrounder that is ("Electronics Components Manufacturing Scheme", PRID
2311234) names no company.

**A release page is a shell.** The release is in
`iframe#ContentPlaceHolder1_iframepressrealese`, and the shell's sidebar of
other releases is where the old parser found its names.
`PressReleaseIframePage.aspx?PRID=N&reg=3&lang=1` is the release alone (130 KB).
Its text is in `div.innner-page-main-about-us-content-right-part` (sic), with
the title in `h1#Titleh2` and "Posted On: 25 SEP 2026 4:36PM by PIB Delhi" in
`#PrDateTime`. The page's ten `<li>` and its one table (the ministry's name)
are outside that block, and the release's text is on the page twice.

**How a release names companies**: in running text, in `<strong>`, with a
legal suffix ("Lyfius Pharma Pvt. Ltd., a subsidiary of Aurobindo Pharma
Limited"), and as "Companies such as GE Healthcare, Siemens, Philips, Varex,
Nipro and Omron", without one. The old parser read "Dr. Reddy's Laboratories
Limited" as "Laboratories Limited" (it allowed no stop or apostrophe inside a
name), missed "Pvt. Ltd." and every name without a suffix, and took any phrase
ending "Industries" for a company. All 18 companies named that day were under
the pharmaceutical, bulk drug and medical device schemes, which no holding works
in: the reason the scraper now reports a beneficiary only under a scheme one
does (`config.PLI_SCHEMES`).

---

## Screener's peer tables cut names short; NSE's equity list has them whole

**Measured 2026-10-15**, run 38730401675 (`probe_upstream.py --source
nse-isin`, which now prints each holding's and competitor's stored name beside
NSE's registered one, and what `analysis/company_names.py` would store).

**Screener's peer tables** label companies in about fifteen characters:
"NTPC Green Ene.", "Oracle Fin.Serv.", "IRB Infra.Devl.", "Kotak Mah. Bank",
initials for the oil refiners ("C P C L"), and cuts with no dot at all ("Data
Pattern", "Inventurus Knowl"). In the 15 Oct peer and candidate tables, 27 of
192 names ended in a dot. The rotation admitted holdings under these labels,
and the matcher, which takes a name only as whole words, matched them to no
headline but by ticker.

**NSE's `EQUITY_L.csv`** carries `NAME OF COMPANY` for every symbol it lists:
2,605 on this run, each with "Limited" (one with "Ltd."). 179 of our 192
holdings and competitors are in it; ASMTEC (BSE-only) and SPELS are not.

Two things about those names decide how they are used:

- **NSE's capitals are not the company's.** "Acme Solar Holdings", "Mtar
  Technologies", "MphasiS", "Ideaforge Technology"; three names are entirely
  in capitals (Sagility, Sigma Advanced Systems, Tata Consumer Products). A
  repaired name keeps the stored spelling of every word it kept whole.
- **A registered name is not always how the news writes the company.**
  "Kalpataru Projects International" is "Kalpataru Projects" in a headline,
  and "Apollo Hospitals Enterprise" is "Apollo Hospitals". So a stored name is
  repaired only when it is the registered name cut down, and the shorter forms
  headlines use are listed in `headline_names.json`.

---

## Screener files ASMTEC under its BSE code, and names a bank's rows differently

**Measured 2026-10-14**, runs 38560166912, 38561213070 and 38561917933
(`probe_upstream.py --source screener-accounts`, which now prints each
page's row labels and asks Screener's search about a page that is not there).

**ASMTEC.** `/company/ASMTEC/` is a 404 under both views. Screener's own
search, `/api/company/search/?q=ASMTEC&v=3&fts=1`, answers with one company:

```
[{"id": 300, "name": "ASM Technologies Ltd", "url": "/company/526433/consolidated/"},
 {"id": null, "name": "Search everywhere: ASMTEC", "url": "/full-text-search/?q=ASMTEC"}]
```

526433 is its BSE code, and that page has everything: market cap ₹10,034 Cr,
P/E 137.0, ROCE 27.0, quarterly sales ₹199 Cr. Searching by name also returns
a partly-paid line, `/company/id/1275222/`, which is not the company's page.
So `providers/screener.py` asks the search once, when neither view is there,
takes a hit only if its name is the holding's, and keeps the page it found
(`slug`) for the next run.

**Banks.** HDFCBANK's and SBIN's pages use Screener's template for lenders:

```
quarters    : Revenue +, Interest, Expenses +, Financing Profit, Financing Margin %,
              Other Income +, Depreciation, Profit before tax, Tax %, Net Profit +,
              EPS in Rs, Gross NPA %, Net NPA %
profit-loss : the same, with Dividend Payout % for the NPA rows
```

The parser looked for "Sales" and "OPM", so all three banks had no
quarterly sales, no margin and no annual sales. "Revenue" (interest earned)
is now read as sales.

"Financing Margin %" sits where other pages have "OPM %", but it is **not an
operating margin**, and the runs that checked this code (38561213070,
38561917933) showed why it must not be read as one: ICICIBANK's
consolidated financing margin was **-12%** and SBIN's -8%, while both made
a profit. It is revenue less interest expended and expenses, provisions
included, and on a consolidated page it leaves out an insurance arm's
income, which Screener puts in Other Income. Read as `q_opm`, it would have
zeroed both banks' Graham values as companies losing money at the operating
line and raised margin warnings. So it is kept as `q_fin_margin` and
`fin_margin_trend`: shown on the results card and given to Ask as a
financing margin, and never scored.

**Ratios table** (run 38569875263, HAL, BEL and HDFCBANK): a company's has
Debtor Days, Inventory Days, Days Payable, Cash Conversion Cycle, Working
Capital Days and ROCE %, one column a year; a lender's has ROE % alone. The
latest working-capital and debtor days are read for the dashboard's
visibility proxy, which stands where an order book would: no source this
pipeline reads publishes one.

---

## Three holdings have no consolidated figures on Screener

**Measured 2026-10-14**, runs 38542728415 and 38557623882
(`probe_upstream.py --source screener-accounts`) and 38557627379
(`--source screener-peers`). Figures in ₹ Cr, from the second run.

Every run read `/company/{T}/consolidated/` and nothing else. For SCHNEIDER,
PAGEIND and RELAXO that page answers 200 with the shareholding and nothing
more. Their standalone page, `/company/{T}/`, carries all of it:

```
consolidated  SCHNEIDER, PAGEIND, RELAXO: 200, 8 fields, no figures, no warehouse id
              HAL: 200, P/E 35.3, warehouse 23511394
              ASMTEC: 404

standalone    SCHNEIDER  mcap 28,655  P/E 148.0  ROCE 29.6  Q sales   651  warehouse 1285
              PAGEIND    mcap 41,184  P/E  52.7  ROCE 64.4  Q sales 1,420  warehouse 3073
              RELAXO     mcap  7,482  P/E  40.4  ROCE 11.2  Q sales   705  warehouse 3182
              HAL        P/E 35.5, warehouse 20540165
              ASMTEC: 404
```

- **A page without figures still parsed to a non-empty dict.** The capex and
  R&D defaults are written for every page, so the three were logged "Screener
  data loaded" each day and marked fetched, which kept the last-known-good
  step from putting anything back. `has_figures()` now decides that.
- **Nothing on the blank page points to the other one.** A page with figures
  heads its tables "Consolidated Figures in Rs. Crores / View Standalone"; the
  blank ones have no such heading, and the word turns up on them only in
  custom KPI rows ("Sales Volume … Standalone data"), on two of the three. So
  the parse decides the fallback, not a notice.
- **The warehouse id differs by view**, and the blank pages had none, so these
  three holdings' industries were never scanned for peers. A standalone id
  works for the peers API: PAGEIND's (3073) returned 7 rows.
- **ASMTEC is a 404 under both views**, so Screener files it under another
  slug, which was not looked for. Its price already comes through the BSE
  fallback. **Still open.**

**Consequence:** `providers/screener.py` reads the consolidated page, then the
standalone one when the first shows no figures or is a 404, and records which
in `accounts`; the dashboard says when a holding's figures are standalone, as
a standalone P/E is not comparable to a peer's consolidated one.

---

## NSE's event calendar and corporate actions answer a runner

**Measured 2026-10-10**, run 38030507295
(`probe_upstream.py --source nse-calendar`).

`providers/nse_calendar.py` was written against the fields NSE's own pages
read, before any of it had been requested from a runner. Both endpoints
answer through the announcements provider's handshake, take the date window,
and use exactly the field names the provider reads first:

```
handshake        : True -> cookies ['AKA_A2', '_abck', 'bm_sz', 'nsit']
event-calendar   : index=equities, from_date=26-09-2026, to_date=09-12-2026
                   200, application/json, 90,915 bytes, list, 351 records
                   fields: bm_desc company date purpose symbol
                   351 of 351 normalised
corporate-actions: same window
                   200, application/json, 7,095 bytes, list, 24 records
                   fields: bcEndDate bcStartDate caBroadcastDate comp exDate
                           faceVal ind isin ndEndDate ndStartDate recDate
                           series subject symbol
                   24 of 24 normalised
```

The window was honoured on the first request, so the provider's fallbacks (the
same request with only `index`, then with no parameters) did not run; they
stay for the day NSE stops taking it. Why there are 24 corporate actions
against 351 board meetings in the same window was not established; the
saved sample (artifact `upstream-sample-nse-calendar`, kept 7 days) is where
to start if the count looks wrong on a later run.

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

## BSE endpoint catalogue — re-measured, nothing moved

**Measured 2026-09-14**, run 34807288884 (`probe-bse.yml`), re-confirming
2026-08-14. A month apart, and every endpoint is exactly where it was.

| Endpoint | Aug 14 | Sep 14 | |
|---|---|---|---|
| BSE bhavcopy | 851 KB, 4,973 rows | 857,324 B, 5,008 lines | works |
| ListofScripData | 1.75 MB, 4,975 scrips | 1,755,863 B, 5,004 | works |
| getScripHeaderData | works | 200, 1,183 B | works |
| AnnSubCategoryGetData | works (from 15 Aug) | serves filings | works |
| NSE EQUITY_L.csv | — | 200, 181,324 B, 2,569 lines | works |
| NSE UDiFF zip | 196 KB | 204,525 B, PK verified | works |
| sec_bhavdata_full | 376 KB, 3,308 rows | 394,927 B, 3,486 lines | works |
| NSE legacy bhavcopy | 404 | 404 | gone for good |
| Shareholding ×4 names | 1,814 B ASP.NET miss | identical | dead |
| AnnGetData | `"No Record Found!"` | identical, 18 B | wrong path |
| Msnew autocomplete | HTML not JSON | identical | dead |

**The scrip master carries more than the August note recorded.** Twelve keys,
not seven: `SCRIP_CD`, `Scrip_Name`, `Status`, `GROUP`, `FACE_VALUE`,
`ISIN_NUMBER`, `INDUSTRY`, `scrip_id`, `Segment`, `NSURL`, `Issuer_Name`,
`Mktcap`. `INDUSTRY` is **null** in the sample, so do not plan on it —
`Issuer_Name` and `NSURL` are the genuinely new usable fields.

**The bot filter is unchanged, and asymmetric.** Same URL, headers on and off:

```
NSE archives, no headers  -> ReadTimeout after 20s
NSE archives, browser UA  -> 200
BSE api,      no headers  -> 403 "Access Denied" (420 bytes)
BSE api,      browser UA  -> 200
```

NSE fails by **hanging** rather than rejecting, which is the more expensive of
the two — a bare request costs the full timeout. The User-Agent and Referer
that `providers/isin_master.py` sends are required, not decorative.

### AnnSubCategoryGetData, measured properly

**2026-09-14**, run 34807792940, asking for a single completed session
(2026-09-11):

```
envelope: {"Table": [...50 records...], "Table1": [{"ROWCNT": 870}]}
record keys: NEWSID, SCRIP_CD, XML_NAME, NEWSSUB, DT_TM, NEWS_DT,
             CRITICALNEWS, ANNOUNCEMENT_TYPE, QUARTER_ID, FILESTATUS,
             ATTACHMENTNAME, MORE, HEADLINE, CATEGORYNAME, OLD, RN
```

**870 announcements for one trading day, 50 to a page.** The control now makes
the August lesson measured rather than narrated: the *same parameters* sent to
`AnnGetData` return `"No Record Found!"` in 18 bytes, while
`AnnSubCategoryGetData` returns 870 records. Identical query, identical 200,
identical content type. Only the path differs.

**The window must be a single day.** `strPrevDate=<7 days ago>` with
`strToDate=<today>` returns `{}` — two bytes, HTTP 200. Whatever the endpoint
does with a range, it is not what a range means, and the empty dict is
indistinguishable from an outage if you are not expecting it.

**Worth a look, not yet changed:** 870 records at 50 a page is 18 pages, and
`providers/bse_announcements.py` sets `MAX_PAGES = 6`. Production therefore
reads roughly 300 of 870 on a normal day. That cap is deliberate and the code
says so ("this is an enrichment, not a crawl", "raise MAX_PAGES if holdings are
being missed") — but it was set before anyone had counted the day's total, and
now we have: it sees about a third. Whether that matters depends on whether
watchlist filings cluster early in BSE's ordering, which is not yet measured.

### What this run changed in the probe itself

The catalogue was re-litigating settled negatives and would have misled a
reader:

- It fired **three** parameter variations at `AnnGetData` and reported
  "No Record Found!" three times — while `providers/bse_announcements.py` had
  been pulling real filings from `AnnSubCategoryGetData` for a month. A
  catalogue whose verdict contradicts the running pipeline is worse than no
  catalogue. It now probes the live path, and keeps **one** `AnnGetData` call
  as a labelled control, because the pair side by side is the lesson: same
  parameters, same 200, same content type, one returns filings and one returns
  a polite empty string.
- It guessed **four** shareholding endpoint names every run, all returning the
  identical generic miss, against a question this method cannot answer. Cut to
  one tripwire.
- `main()` printed "Probe complete" regardless of outcome — the same
  "did not raise ≠ answered" error corrected in `probe_upstream.py`. It now
  reports each endpoint against what is **expected**, so a known-dead endpoint
  staying dead reads differently from a working one regressing. Without that
  distinction a real regression hides among the failures that are supposed to
  be there.

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
