## 2026-06-19 - Synchronous HTTP Request Bottleneck in Watchlist Curation
**Learning:** Found a performance bottleneck in `metrics.py` where `auto_curate_watchlist` was making multiple sequential `requests.get()` calls to Screener.in and Yahoo Finance during loop iterations, causing severe TCP/SSL handshake overhead.
**Action:** When performing multiple synchronous HTTP requests in a loop, always utilize `requests.Session()` to enable connection pooling.
