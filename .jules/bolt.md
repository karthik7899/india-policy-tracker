## 2024-06-17 - Watchlist Flattening Optimization
**Learning:** Optimizing sub-string checks against dictionaries-of-lists can yield ~50% speedup by pre-flattening into tuples and hoisting `.lower()` calls out of loops. Replacing O(N) substring scans with O(1) hash maps is functionally breaking when substring matching is semantically required.
**Action:** Identify loop invariants in hot paths (like case conversions) and pre-compute flattening operations over read-only data structures outside iteration boundaries.
