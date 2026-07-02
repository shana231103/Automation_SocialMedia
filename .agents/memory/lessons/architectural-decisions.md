# Architectural Decisions

### 2026-07-02 — Unified Automation Service Port
**Context:** The codebase originally had separate endpoints and execution scripts for DrissionPage and Playwright.
**Problem:** Changing from DrissionPage to Playwright required API consumers to call different endpoints and forced UI code duplication.
**Resolution:** Implemented an abstraction boundary using `AutomationService` and `BrowserContextManager` in the application layer. The choice of browser engine is now governed by the `AUTOMATION_PROVIDER` variable inside `.env` files.
**Impact:** Swapping the underlying browser automation driver does not affect presentation APIs or UI components.
**Recommendation:** Any new driver (e.g. Selenium or GoLogin) must implement `BrowserContextManager` and be registered inside the factory.
