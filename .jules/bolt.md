## 2026-06-14 - Python Connection Pooling
**Learning:** Found an anti-pattern where multiple synchronous HTTP requests were being made sequentially without using connection pooling, incurring significant TCP/SSL handshake overhead for domains like `finance.yahoo.com` and `screener.in`.
**Action:** When working with multiple synchronous HTTP requests in Python scripts, specifically when repeatedly hitting the same APIs in loops, create a module-level or global `requests.Session()` to enable connection reuse.
