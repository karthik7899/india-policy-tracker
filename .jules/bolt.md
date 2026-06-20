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
