## 2024-10-24 - Sync HTTP Connection Pooling
**Learning:** Making multiple synchronous HTTP requests (e.g., in `metrics.py`) without a `requests.Session` causes redundant TCP/SSL handshake overhead.
**Action:** Always use a `requests.Session()` for connection pooling when making multiple synchronous requests to the same domains, especially in loops like `auto_curate_watchlist`.
