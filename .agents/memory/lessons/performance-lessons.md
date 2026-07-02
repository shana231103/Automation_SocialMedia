# Performance Lessons

### 2026-07-02 — Thread Blocking with DrissionPage in FastAPI
**Context:** FastAPI handles API calls asynchronously. DrissionPage is a synchronous automation library.
**Problem:** Invoking DrissionPage scripts directly from routes blocked FastAPI's single-threaded event loop, preventing concurrent requests or status updates from loading.
**Resolution:** Wrapped synchronous DrissionPage automation sessions inside a thread execution pool using `asyncio.to_thread` or running within executors.
**Impact:** Allows concurrent FastAPI endpoints to execute while browser sessions are running in separate worker threads.
**Recommendation:** Do not call synchronous browser tasks directly. Use executors or thread delegation.
