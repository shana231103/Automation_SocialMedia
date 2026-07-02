# Migration Notes

### 2026-07-02 — DB Backend Migration to PostgreSQL
**Context:** Early mock iterations used sqlite or memory databases for tracking login records.
**Problem:** Concurrency limits and loss of state on container restart.
**Resolution:** Updated `connection.py` to target PostgreSQL and created database schema verification functions (`create_db.py`) loaded on service startup.
**Impact:** Enabled persistent logging across container lifecycles.
**Recommendation:** Check database server connectivity before launching the backend using standard environment checks.
