## 2026-06-17 - Large Function Refactoring Verification
 **Learning:** When refactoring exceptionally large functions that span multiple output truncations, estimating line numbers for replacement blocks often leads to errors and unverified logic assumptions.
 **Action:** Next time, extract helper functions iteratively or use smaller `sed` window commands (e.g., 20-30 lines) to fully map the function boundaries before attempting any large scale code replacement.
## 2024-06-17 - Watchlist Flattening Optimization
**Learning:** Optimizing sub-string checks against dictionaries-of-lists can yield ~50% speedup by pre-flattening into tuples and hoisting `.lower()` calls out of loops. Replacing O(N) substring scans with O(1) hash maps is functionally breaking when substring matching is semantically required.
**Action:** Identify loop invariants in hot paths (like case conversions) and pre-compute flattening operations over read-only data structures outside iteration boundaries.
## 2026-06-17 - Asynchronous Ticker Resolution Optimization
 **Learning:** Sequential synchronous network calls (`requests.get`) inside loops, even when wrapped in a larger async function, cause significant event-loop blocking and performance degradation. Converting these calls to use `aiohttp.ClientSession` and gathering them concurrently via `asyncio.gather` yields massive speedups (from ~1.9s to ~0.27s for 10 sequential calls).
 **Action:** When refactoring functions that perform HTTP requests inside loops to be asynchronous, pre-gather a unique list of targets and execute all requests concurrently using `asyncio.gather` rather than awaiting them one-by-one inside a loop.
## 2026-06-14 - Python Connection Pooling
**Learning:** Found an anti-pattern where multiple synchronous HTTP requests were being made sequentially without using connection pooling, incurring significant TCP/SSL handshake overhead for domains like `finance.yahoo.com` and `screener.in`.
**Action:** When working with multiple synchronous HTTP requests in Python scripts, specifically when repeatedly hitting the same APIs in loops, create a module-level or global `requests.Session()` to enable connection reuse.
## 2024-10-24 - Sync HTTP Connection Pooling
**Learning:** Making multiple synchronous HTTP requests (e.g., in `metrics.py`) without a `requests.Session` causes redundant TCP/SSL handshake overhead.
**Action:** Always use a `requests.Session()` for connection pooling when making multiple synchronous requests to the same domains, especially in loops like `auto_curate_watchlist`.
## 2026-06-13 - Rate Limits with yfinance batching and concurrency
**Learning:** `yf.download` is much faster for a batch of tickers than calling `yf.Ticker(t).history(period="1d")` in a `ThreadPoolExecutor` and avoids rate limits. But getting `info` requires individual requests which takes time and can hit limits. The problem in the review was using `fast_info` in `try/except Exception`, but `info` was still being accessed immediately after. `ticker.info` requires an API call that rate limits us.
Actually, the reviewer pointed out that changing `ticker_obj.history(period="1d")` to `ticker_obj.fast_info.last_price` CAUSED the performance drop. That is likely because `fast_info` gets rate limited and takes long time when done concurrently, whereas `history()` is optimized better or uses a different endpoint that didn't rate limit in their environment.

**Action:** Revert changes to use `fast_info`. The correct optimization is `yf.download` to fetch all history in one go at the start, or pass a shared `requests.Session()` to `yf.Ticker(t, session=shared_session)`.
## 2024-06-16 - Synchronous Requests Bottleneck in Auto-Curation
**Learning:** Found a performance bottleneck in `metrics.py` where `auto_curate_watchlist` was making multiple synchronous API calls using `requests.get()` inside a loop (for both ticker resolution and Screener.in checks). This caused significant overhead due to repeated TCP connection setups and SSL handshakes.
**Action:** Always instantiate a `requests.Session()` object when making multiple synchronous requests to the same or even different domains to benefit from connection pooling, which reuses the underlying TCP connections.
## 2024-06-17 - Connection Pooling for Repeated HTTP Requests
**Learning:** Making multiple synchronous HTTP requests (e.g. evaluating candidates in `auto_curate_watchlist` which performs Screener and Yahoo Finance lookups) using `requests.get` incurs repeated TCP/SSL handshake overhead, which acts as a performance bottleneck specific to this kind of iterative loop architecture.
**Action:** When a loop involves multiple synchronous `requests.get` calls, instantiate a `requests.Session()` outside the loop and reuse the session inside for connection pooling to avoid redundant handshake overhead.
## 2026-06-18 - Connection Pooling for Synchronous HTTP Requests
**Learning:** In a mixed codebase (using `aiohttp` and `requests`), running multiple synchronous HTTP requests sequentially without connection pooling (e.g. inside a loop using `requests.get`) creates a significant performance overhead due to repeated TCP/SSL handshakes.
**Action:** Always instantiate a `requests.Session()` object when making multiple contiguous, synchronous HTTP requests to reuse the underlying connection.
## 2026-06-19 - Synchronous HTTP Request Bottleneck in Watchlist Curation
**Learning:** Found a performance bottleneck in `metrics.py` where `auto_curate_watchlist` was making multiple sequential `requests.get()` calls to Screener.in and Yahoo Finance during loop iterations, causing severe TCP/SSL handshake overhead.
**Action:** When performing multiple synchronous HTTP requests in a loop, always utilize `requests.Session()` to enable connection pooling.

## 2026-06-20 - Thread-safe Connection Pooling for Concurrent yfinance Info Fetches
**Learning:** When using `ThreadPoolExecutor` to fetch Yahoo Finance `info` concurrently for multiple tickers (e.g., in `analysis/growth.py`), creating a new underlying HTTP connection per thread incurs high TCP/SSL handshake overhead and increases the likelihood of hitting rate limits. `requests.Session` is thread-safe and pooling works across threads.
**Action:** Instantiate a single `requests.Session()` before launching the thread pool, and pass this shared session to the worker threads (and ultimately to `yfinance`) to pool connections across concurrent fetches.

## 2026-07-02 - Correction: do not pass a custom session into yf.Ticker
**Learning:** The 2026-06-13 and 2026-06-20 entries above are wrong for `yfinance.Ticker` specifically (flagged by Codex review on PRs #41/#42). `yfinance`'s `YfData` is already a process-wide singleton holding one pooled, curl_cffi-backed session reused across all threads, so passing a custom `requests.Session()` adds no extra pooling. Worse, concurrent threads calling `yf.Ticker(session=...)` each reassign the shared singleton's session (a race), and a plain `requests.Session` lacks yfinance's browser-impersonation headers, which can cause ticker fetches to silently fail (the exception gets swallowed per-stock, leaving stale prices).
**Action:** Never pass a custom `requests.Session` into `yf.Ticker`/`fetch_stock_data`; let yfinance manage its own session. The `yf.download()` batch-fetch pattern (unaffected by this issue) remains the right way to reduce per-ticker overhead.
## 2026-06-25 - Pre-flattening Nested List Checks
**Learning:** Checking for ticker existence in a dictionary of lists (like `watchlist`) within a loop causes unnecessary O(N) traversal.
**Action:** Always pre-flatten the dictionary of lists into a `set` (e.g. `watchlisted_tickers = {x["ticker"] for s_list in watchlist.values() for x in s_list}`) outside the loop for O(1) lookups. Ensure you update the set when mutating the original list.

## 2026-06-25 - Async Ticker Resolution Overhead
**Learning:** Found an anti-pattern in `scrape_pib_pli_approvals_async` where synchronous `resolve_ticker_from_name` calls were placed inside a loop iterating over candidate competitors, causing event-loop blocking and degrading scraping performance.
**Action:** When gathering data asynchronously, ensure auxiliary lookups (like ticker resolution) within candidate loops use async HTTP libraries and are gathered concurrently with `asyncio.gather` to preserve the benefits of asynchronous IO.

## 2026-07-10 - Headline Name Matching Memoization
**Learning:** The string and regex tokenization of market headlines (titles) and company names in `title_matches_company` is executed heavily in deep loops during headline classification and pipeline candidate evaluation. Re-computing these allocations caused significant redundant overhead.
**Action:** Use `functools.lru_cache` to memoize string processing and regex operations in hot loops. Ensure the cached helper functions return immutable data structures (like tuples or frozensets) to prevent unintentional mutation side effects.
