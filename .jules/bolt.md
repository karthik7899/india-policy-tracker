## 2026-06-18 - Connection Pooling for Synchronous HTTP Requests
**Learning:** In a mixed codebase (using `aiohttp` and `requests`), running multiple synchronous HTTP requests sequentially without connection pooling (e.g. inside a loop using `requests.get`) creates a significant performance overhead due to repeated TCP/SSL handshakes.
**Action:** Always instantiate a `requests.Session()` object when making multiple contiguous, synchronous HTTP requests to reuse the underlying connection.
## 2026-06-19 - Synchronous HTTP Request Bottleneck in Watchlist Curation
**Learning:** Found a performance bottleneck in `metrics.py` where `auto_curate_watchlist` was making multiple sequential `requests.get()` calls to Screener.in and Yahoo Finance during loop iterations, causing severe TCP/SSL handshake overhead.
**Action:** When performing multiple synchronous HTTP requests in a loop, always utilize `requests.Session()` to enable connection pooling.
