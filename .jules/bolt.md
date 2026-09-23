# Bolt performance learnings

**Newest first.** That ordering is not cosmetic: a correction is always
written after the thing it corrects, so newest-first guarantees a retraction
is read before the advice it overturns. This file was previously chronological
in places and shuffled in others, which put the 2026-07-02 correction *below*
both entries it retracts — an agent reading top-down met the wrong advice
three times before the fix.

Retracted entries are kept rather than deleted, because knowing an approach
was tried and why it failed is worth more than a clean file. Each carries a
banner naming what superseded it.

> **RETRACTED, read this first:** never pass a custom `requests.Session` into
> `yf.Ticker` / `fetch_stock_data`. Three entries below recommend it
> (2026-06-20, and the closing clause of 2026-06-13). All are superseded by
> **2026-07-02**. The `yf.download()` batch pattern is unaffected and remains
> correct.

---

## 2026-08-17 - Unintended Concurrent API Calls Despite Batching
**Learning:** Adding `yf.download()` to batch fetch prices improved performance, but it failed to realize its full benefit because the downstream `fetch_stock_data()` function still unconditionally invoked `ticker_obj.history(period="1d")` for each stock independently in a ThreadPoolExecutor. This caused a redundant network request per ticker, essentially neutralizing the batch fetch optimization for prices.
**Action:** When adding batch fetching optimizations upstream, explicitly pass flags downstream (e.g. `fetch_price=False`) or update the downstream logic to skip the redundant single-item API calls if the data is already pre-fetched.

## 2026-07-10 - Headline Name Matching Memoization
**Learning:** The string and regex tokenization of market headlines (titles) and company names in `title_matches_company` is executed heavily in deep loops during headline classification and pipeline candidate evaluation. Re-computing these allocations caused significant redundant overhead.
**Action:** Use `functools.lru_cache` to memoize string processing and regex operations in hot loops. Ensure the cached helper functions return immutable data structures (like tuples or frozensets) to prevent unintentional mutation side effects.

## 2026-07-02 - Correction: do not pass a custom session into yf.Ticker
**Supersedes:** the 2026-06-20 entry, and the closing clause of 2026-06-13.
**Learning:** The 2026-06-13 and 2026-06-20 entries below are wrong for `yfinance.Ticker` specifically (flagged by Codex review on PRs #41/#42). `yfinance`'s `YfData` is already a process-wide singleton holding one pooled, curl_cffi-backed session reused across all threads, so passing a custom `requests.Session()` adds no extra pooling. Worse, concurrent threads calling `yf.Ticker(session=...)` each reassign the shared singleton's session (a race), and a plain `requests.Session` lacks yfinance's browser-impersonation headers, which can cause ticker fetches to silently fail (the exception gets swallowed per-stock, leaving stale prices).
**Action:** Never pass a custom `requests.Session` into `yf.Ticker`/`fetch_stock_data`; let yfinance manage its own session. The `yf.download()` batch-fetch pattern (unaffected by this issue) remains the right way to reduce per-ticker overhead.

## 2026-06-25 - High-Performance HTML Stripping
**Learning:** For high-performance HTML tag stripping in hot loops (e.g., RSS feed parsing), `BeautifulSoup` introduces significant overhead (taking ~1.8s for 10k parses vs ~0.05s for regex). `BeautifulSoup` should be avoided for simple text extraction where full DOM parsing is unnecessary.
**Action:** Use regex (`re.sub(r'<[^>]+>', '', text)`) and `html.unescape()` instead of `BeautifulSoup` for massive speedups (50x-100x) when merely stripping tags from strings like RSS titles and summaries.

## 2026-06-17 / 2026-06-25 - Sequential IO inside async loops
**Recorded twice**, for two call sites, with the same conclusion.

**Learning:** Synchronous network calls (`requests.get`) inside a loop block the event loop even when the enclosing function is `async`, so the code reads as concurrent and behaves as serial. Measured at ~1.9s vs ~0.27s for ten calls. Seen in ticker resolution generally, and specifically in `scrape_pib_pli_approvals_async`, where `resolve_ticker_from_name` was called synchronously per candidate competitor.
**Action:** Pre-gather a unique list of targets, use `aiohttp` rather than `requests`, and run them with `asyncio.gather` instead of awaiting one at a time. Applies to auxiliary lookups inside candidate loops too, not just the obvious top-level fetches.

## 2026-06-25 - Pre-flattening Nested List Checks
**Learning:** Checking for ticker existence in a dictionary of lists (like `watchlist`) within a loop causes unnecessary O(N) traversal.
**Action:** Always pre-flatten the dictionary of lists into a `set` (e.g. `watchlisted_tickers = {x["ticker"] for s_list in watchlist.values() for x in s_list}`) outside the loop for O(1) lookups. Ensure you update the set when mutating the original list.

## 2026-06-20 - Thread-safe Connection Pooling for Concurrent yfinance Info Fetches
> ⛔ **RETRACTED by 2026-07-02.** Do not act on the Action below. Passing a
> custom session into `yf.Ticker` races on yfinance's singleton and can make
> ticker fetches fail silently. Kept for the record only.

**Learning:** When using `ThreadPoolExecutor` to fetch Yahoo Finance `info` concurrently for multiple tickers (e.g., in `analysis/growth.py`), creating a new underlying HTTP connection per thread incurs high TCP/SSL handshake overhead and increases the likelihood of hitting rate limits. `requests.Session` is thread-safe and pooling works across threads.
**Action:** Instantiate a single `requests.Session()` before launching the thread pool, and pass this shared session to the worker threads (and ultimately to `yfinance`) to pool connections across concurrent fetches.

## 2026-06-14 → 2026-06-19 - Use requests.Session for synchronous HTTP in loops
**Rediscovered independently six times** (2024-06-16, 2024-06-17, 2024-10-24,
2026-06-14, 2026-06-18, 2026-06-19) before anyone noticed it was already
written down. The repetition is kept as a count rather than as six entries,
because the fact that it happened six times says something the sixth copy did
not: this file was being appended to and not read.

**Learning:** Multiple synchronous HTTP requests issued sequentially without connection pooling incur repeated TCP/SSL handshake overhead. Observed in `metrics.py` (`auto_curate_watchlist`, doing ticker resolution and Screener.in lookups in a loop) and against `finance.yahoo.com` and `screener.in` generally, including in mixed codebases that already use `aiohttp` elsewhere.
**Action:** Instantiate one `requests.Session()` outside the loop and reuse it, so the underlying TCP connection is pooled across requests.
**Does NOT apply to `yf.Ticker`** — see the 2026-07-02 correction above.

## 2026-06-17 - Large Function Refactoring Verification
**Learning:** When refactoring exceptionally large functions that span multiple output truncations, estimating line numbers for replacement blocks often leads to errors and unverified logic assumptions.
**Action:** Next time, extract helper functions iteratively or use smaller `sed` window commands (e.g., 20-30 lines) to fully map the function boundaries before attempting any large scale code replacement.

## 2026-06-13 - Rate Limits with yfinance batching and concurrency
> ⛔ **The closing clause of the Action below is RETRACTED by 2026-07-02** —
> do not pass a shared `requests.Session()` into `yf.Ticker`. The rest of this
> entry stands, and its `yf.download()` recommendation is still the right one.

**Learning:** `yf.download` is much faster for a batch of tickers than calling `yf.Ticker(t).history(period="1d")` in a `ThreadPoolExecutor` and avoids rate limits. But getting `info` requires individual requests which takes time and can hit limits. The problem in the review was using `fast_info` in `try/except Exception`, but `info` was still being accessed immediately after. `ticker.info` requires an API call that rate limits us.
Actually, the reviewer pointed out that changing `ticker_obj.history(period="1d")` to `ticker_obj.fast_info.last_price` CAUSED the performance drop. That is likely because `fast_info` gets rate limited and takes long time when done concurrently, whereas `history()` is optimized better or uses a different endpoint that didn't rate limit in their environment.

**Action:** Revert changes to use `fast_info`. The correct optimization is `yf.download` to fetch all history in one go at the start, or pass a shared `requests.Session()` to `yf.Ticker(t, session=shared_session)`.

---

The entry below is dated 2024, as were three of the six folded into the
pooling entry above. Every other entry is 2026 and they describe the same
`metrics.py` and `auto_curate_watchlist` work, so the years are very likely
typos. Left as written rather than corrected, because guessing at a date is
how a record stops being one — change them only if you know what they should
say.

## 2024-06-17 - Watchlist Flattening Optimization
**Learning:** Optimizing sub-string checks against dictionaries-of-lists can yield ~50% speedup by pre-flattening into tuples and hoisting `.lower()` calls out of loops. Replacing O(N) substring scans with O(1) hash maps is functionally breaking when substring matching is semantically required.
**Action:** Identify loop invariants in hot paths (like case conversions) and pre-compute flattening operations over read-only data structures outside iteration boundaries.


## 2026-08-18 - Concurrent execution of I/O within async loops
**Learning:** Sequential `await` calls inside a `for` loop block the asynchronous event loop, negating the benefits of using `async`. This was identified in `scrape_pib_pli_approvals_async` where up to 5 HTML article fetches were awaited consecutively.
**Action:** Extract the body of the loop into an inner async helper function (e.g., `async def process_entry(entry):`) and execute them concurrently using `await asyncio.gather(*[process_entry(e) for e in entries])`.
