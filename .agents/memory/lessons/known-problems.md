# Known Problems

### 2026-07-02 — Zombie Browser Instances
**Context:** When a login automation script crashed or was cancelled by the user mid-run, the Chrome browser spawned in headless/headed mode remained open as a zombie process.
**Problem:** Accumulating zombie processes led to memory leaks and blocked port bindings on the host machine.
**Resolution:** Wrapped browser operations inside Python context managers (`__enter__` and `__exit__`). Added explicit try-finally blocks inside `__exit__` to guarantee that `.quit()` or `.close()` is executed even during sudden execution cancellation.
**Impact:** Drastically reduced process leaks during local testing.
**Recommendation:** Always access automation services within a `with` statement.
