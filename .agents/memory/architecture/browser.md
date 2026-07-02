# Architecture: Browser Automation Management

This document details the browser automation architecture, explaining how different driver types and profile systems are managed under a unified interface.

## Responsibility
The Browser Automation Management system is responsible for:
1. **Dynamic Driver Resolution**: Resolving whether to use DrissionPage or Playwright at runtime using environment settings (`AUTOMATION_PROVIDER`).
2. **Profile Management**: Starting/stopping local browser instances or orchestrating antidetect browser profiles (GemLogin) via their REST APIs.
3. **Session Lifecycle & Clean Exit**: Guaranteeing that browser windows and background driver processes are clean-killed when execution is completed, even in cases of network timeouts, uncaught errors, or user cancellation.
4. **Activity Monitoring & Screen Capture**: Providing progress logs and saving error snapshots to files for diagnostic review.

## Interactions & Interfaces

The core interfaces are defined in the Application layer, keeping presentation and infrastructure decoupled.

### `BrowserContextManager`
An abstract context manager (`__enter__` and `__exit__`) that sets up a browser page instance and handles its disposal.
- `get_new_logs()`: Returns logs generated during the session.
- `__enter__()`: Starts the browser and returns the active page control object.
- `__exit__(exc_type, exc_val, exc_tb)`: Shuts down the browser, captures screenshots if `exc_val` is not None, and handles cleanup.

### Interface Hierarchy

```
BrowserContextManager (ABC)
├── DrissionPage (local_browser / gemlogin_browser)
└── Playwright (playwright_browser)
```

## Supported Drivers and Managers

### 1. DrissionPage Drivers (`backend/app/infrastructure/automation/`)
- **`LocalBrowser`**: Launches standard local Chrome profiles using command line flags. Connects via DrissionPage control interfaces.
- **`GemLoginBrowser`**: Issues a POST request to GemLogin's profile REST API to start the profile on a designated debug port, then attaches a DrissionPage Chromium driver to that port.

### 2. Playwright Drivers (`backend/app/infrastructure/automation/`)
- **`PlaywrightBrowser`**: Handles both local Chromium/Chrome profiles and GemLogin profiles. 
  - For GemLogin, it calls the REST API to start the profile, retrieves the `wsEndpoint` or `debuggerAddress` from the response, and uses Playwright's `connect_over_cdp` to attach to it.
  - For local profiles, it launches Chromium directly using Playwright context options.

## Multi-Driver Automation Services

### `AutomationService`
An interface defining the contract for executing logins.
- `run_login(...)`: Accepts login parameters and yields progress logs and the final result.

Implementation classes:
- **`DrissionPageService`**: Automates login steps (finding inputs, typing, clicking buttons, verifying cookies) using DrissionPage elements.
- **`PlaywrightService`**: Performs identical automation steps using Playwright's async API.

## Known Constraints
- **Port Mapping**: Only one driver session can attach to a specific antidetect profile port at a time.
- **Async vs Sync**: Playwright uses Python's `asyncio` APIs, requiring presentation calls to run in an async loop. DrissionPage is synchronous, which must be run inside thread executors to prevent blocking FastAPI's main thread loop.
