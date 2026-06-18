## 2026-06-18 - Connection Pooling for Synchronous HTTP Requests
**Learning:** In a mixed codebase (using `aiohttp` and `requests`), running multiple synchronous HTTP requests sequentially without connection pooling (e.g. inside a loop using `requests.get`) creates a significant performance overhead due to repeated TCP/SSL handshakes.
**Action:** Always instantiate a `requests.Session()` object when making multiple contiguous, synchronous HTTP requests to reuse the underlying connection.
