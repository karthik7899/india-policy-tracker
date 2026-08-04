# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

An automated pipeline that scrapes Indian government policy announcements (PIB releases, RSS/news feeds, SEBI filings, exchange filings, institutional flows) and maps their sector impact onto a curated stock watchlist. It runs on a GitHub Actions cron, commits its own output JSON back into the repo, emails an HTML digest, and serves a static vanilla-JS dashboard (`index.html` + `app.js`) reading that committed JSON via GitHub Pages.

## Commands

```bash
# Install Python deps
pip install -r requirements.txt

# Run the full pipeline locally (writes dashboard_data.json, history.json,
# watchlist.json, rotation_ledger.json; also drops a local email_preview.html)
python main.py
# brief.py is a thin backwards-compatible wrapper around the same entrypoint

# Serve the dashboard locally
python -m http.server 8000   # then open http://localhost:8000

# Lint / format (CI runs both, `black --check` then `flake8`)
black .
flake8 .

# Python tests
python -m pytest tests/
python -m pytest tests/test_scoring.py
python -m pytest tests/test_scoring.py::test_promoter_exit_costs_points
pip install pytest-anyio   # needed for the async tests (tests/test_retry.py etc.)

# JS tests (dashboard logic in app.js)
npm test          # jest, jsdom environment
npx jest app.test.js
npx jest formatGrowthBadge.test.js
```

There is no `conftest.py`; async tests use bare `@pytest.mark.anyio`.

## Architecture

### Pipeline entrypoint

`main.py:run_pipeline()` is the single orchestrator, run via `python main.py` (or the `brief.py` compat wrapper). It is a long, deliberately linear async function — read it top to bottom to understand execution order and *why* steps are sequenced the way they are; most non-obvious ordering is explained in inline comments (e.g. rotation runs before the Screener fetch, revenue growth is computed before scoring, ISIN annotation is repeated because the Screener fetch rebuilds each stock's dict from scratch).

Two concurrency models coexist on purpose and must **not** be merged:
- `asyncio`/`aiohttp` for the scrapers and Screener.in fetches.
- `ThreadPoolExecutor`/`requests` for `yfinance`, which is sync-only.

`yfinance` specifically: never pass a custom `requests.Session` into `yf.Ticker`/`fetch_stock_data`. Its `YfData` singleton already pools one curl_cffi-backed session process-wide with browser-impersonation headers; injecting a plain session races the singleton and can silently break price fetches. Use `yf.download()` for batch fetches instead.

### Data layer / persistence

- `config.py` — `SECTOR_METADATA` (sector labels/icons/descriptions) and `STOCK_WATCHLIST` (minimal fallback seed used **only** if `watchlist.json` is missing/corrupt — never add live market data here, only stable fields like ticker/name/catalyst). Also owns `load_watchlist()`/`save_watchlist()`.
- `watchlist.json` — the live, pipeline-mutated portfolio (prices, ratings, fundamentals, screener data). Auto-curated: `analysis/rotation.py` discovers emerging competitors and rotates out weaker holdings against a 15% QoQ revenue growth threshold.
- `history.json` / `history/store.py` (`HistoryStore`) — the full accumulated corpus across runs, used for cross-run deduplication (`deduplicate_and_merge`) and by consumers that need the accumulated feed rather than a trimmed one.
- `dashboard_data.json` — trimmed **display** copy written by `dashboard/payload.py:build_display_payload()`, consumed whole by the browser on every page load. History and dashboard payload are deliberately separate so trimming for the frontend never shrinks what the pipeline itself computes on.
- `isin_master.json` / `providers/isin_master.py` — symbol→ISIN identity map, refreshed each run; used by `entities.py` to catch the same company silently tracked under two sectors (a duplicate-holding bug class that has actually happened — see DIXON in comments).
- `entity_graph.json` / `analysis/entity_graph.py` — a relationship graph (e.g. corporate tie-ups) that grows itself from harvested headline data, feeding second-order signals like supply-chain stress.
- `rotation_ledger.json` / `analysis/postmortem.py` — logs every rotation decision and later scores it against outcomes, producing a hit-rate metric.
- All of the above JSON files are committed automatically by the `daily-brief.yml` workflow after a successful run — they are pipeline output, not hand-maintained data (aside from `watchlist.json`'s initial curation and `config.py`'s fallback seed).

### `providers/` — external data fetchers

`screener.py` (Screener.in fundamentals + industry peer tables), `yahoo.py` (live prices via yfinance), `rss.py` (news feed parsing), `isin_master.py` (symbol/ISIN resolution).

### `scraper.py`

PIB (Press Information Bureau) release scraping and the various `*_async` feed fetchers imported by `main.py` (advanced RSS, SEBI SID filings, institutional activity, exchange filings, global market events).

### `analysis/` — the business logic

This is where most domain logic lives, one concern per module:
- **Valuation/scoring**: `graham.py` (Benjamin Graham intrinsic value / defensive screens), `buffett.py` (owner earnings, $1 retained-earnings test), `moat.py`, `valuation.py`, `scoring.py` (aggregate score — fundamental vs. momentum kept separate so one can't drown out the other), `sector_valuation.py` (peer P/E relative valuation).
- **Growth/rotation**: `growth.py` (live price updates), `sector_growth.py`, `curve_stage.py` (S-curve sector staging), `rotation.py` (auto-curation), `candidate_screen.py` (quantitative peer screening), `market_share.py`.
- **Signals**: `early_warning.py` (severity-ranked feed synthesized from signals collected elsewhere in the pipeline — does not scrape anything itself), `competitive_intel.py` (new-entrant detection), `event_engine.py` (generic "classify WHAT happened, route to WHO it touches" headline classifier), `revisions.py` (estimate-revision momentum vs. prior run), `variant_perception.py` (where the model's Graham estimate diverges from analyst consensus), `thesis.py` (thesis-health / kill-criteria check per holding), `stock_topics.py` (attributes headlines to the specific company they name, not just its sector).
- **Support**: `parsing.py` (company-name/headline matching — hot loop, uses `functools.lru_cache`), `data_quality.py`, `postmortem.py`, `backtesting.py` (AMFI mutual-fund NAV baseline), `entity_graph.py`.

### `dashboard/`

`builder.py:build_dashboard_views()` compiles the per-company `Company`/`CompanyValuation`/`CompanyFinancials` analytics (Graham/Buffett/moat/scoring) into `data`. `payload.py:build_display_payload()` trims the full corpus down to what the frontend actually renders, and `annotate_warning_status()` diffs this run's early warnings against the prior run so the dashboard can lead with what's new.

### `emails/mailer.py`

Builds the HTML digest and sends it via SMTP. Gmail clips messages over ~102KB: the email renders at full richness first, and if it exceeds `_SIZE_BUDGET_BYTES` (95KB), it re-renders once with compact caps (`_CAPS_NORMAL`) — guaranteed delivery over marginal extra content.

### `models/`

Pydantic models. `core.py` holds the analytics-facing models (`Company`, `CompanyFinancials`, `CompanyValuation`, `CompanyScore`, event/filing models). `stock.py` holds `Stock`, the canonical typed view of a watchlist record: numeric fields are stored as real numbers internally but round-trip back to the legacy display-string wire format (`"482.95"`, `"+23.0%"`) via `to_wire_values()`, so string-vs-number parsing happens in exactly one place instead of ad hoc at every consumer.

### Operational scripts

- `health.py:log_run_health()` — post-run sanity check; runs *after* the email send (a degraded briefing is still worth sending) but decides whether the CI job reports success/failure.
- `market_calendar.py` — hand-maintained NSE holiday list (`NSE_HOLIDAYS_2026`, refresh annually from NSE's circular) gating the **daily** cron only; the Saturday weekly digest and manual `workflow_dispatch` runs always fire regardless.
- `alerts.py` — standard-library-only (no third-party deps) failure notifier invoked by CI when the pipeline job fails; always exits 0 so a broken mailbox can't mask the real failure.
- `utils.py` — shared helpers: `safe_float`/`safe_int`/`to_float` coercion, `atomic_write_json`, `retry_network` decorator, `fetch_text_sync`/`fetch_text_async`.

### Frontend

`index.html` + `app.js` (vanilla JS, no framework/build step) + `styles.css`. `app.js` embeds `MOCK_DATA` as a fallback seed matching `dashboard_data.json`'s shape, then fetches the real file at runtime. Tested with Jest/jsdom (`app.test.js`, `formatGrowthBadge.test.js`).

## CI/CD

- `.github/workflows/ci.yml` — on PR/push to `main`: `black --check .`, `flake8 .`, `pytest tests/`.
- `.github/workflows/daily-brief.yml` — scheduled pipeline runner:
  - `quality` job runs the same lint/test suite but **never blocks** the briefing job — a formatting nit must never stop the daily email (it did once, for three days).
  - `run-briefing` job gates the *daily* cron on `market_calendar.is_trading_day()` (weekly Saturday digest and manual dispatch bypass the gate), runs `python main.py` with SMTP secrets, then commits the pipeline's output JSON files back to `main` (rebase-and-retry if another run pushed first) — gated implicitly on job success so a degraded run never overwrites committed data with partial output.
  - On any job failure, runs `alerts.py` to notify out-of-band.

## Conventions

- `black` + `flake8` (max line length 250; see `.flake8` for the full ignore list) — run both before considering Python changes done.
- Prefer `requests.Session()` for connection pooling whenever making multiple synchronous HTTP calls to the same host in a loop — **except** `yfinance`, per the note above.
- For hot loops over headline/name text, prefer regex + `html.unescape()` over BeautifulSoup, and `functools.lru_cache` for repeated string/regex work (see `analysis/parsing.py`).
- When gathering many async requests in a loop, collect targets first and run them concurrently with `asyncio.gather` rather than awaiting sequentially inside the loop.
- Pre-flatten dict-of-lists lookups (e.g. ticker membership across watchlist sectors) into a `set` outside loops instead of repeated linear scans — keep the set updated if the source list mutates.
