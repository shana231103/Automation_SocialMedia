# Implementation Pitfalls

### 2026-07-02 — Hardcoded GemLogin Ports
**Context:** During early testing, GemLogin's profile listener port was assumed to be `http://localhost:1010/api` persistently.
**Problem:** In custom client environments, the port might change or be occupied, crashing the wrapper class.
**Resolution:** Expose the REST API connection URL through environment variables (`GEMLOGIN_API_URL`) and check connectivity during initialization.
**Impact:** Enabled runtime verification of profile listeners.
**Recommendation:** Always validate that the antidetect controller API is reachable before starting profile automation steps.
