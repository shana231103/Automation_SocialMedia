# Service: AutomationService

## Responsibility
The `AutomationService` is responsible for automating the sequence of operations required to log into Facebook, YouTube, TikTok, or Twitter (X) and determining the outcome state (logged in, logged out, checkpoint, or dead).

## Public Methods

### `run_login(username, password, platform, profile_key)`
- **Parameters**:
  - `username` (str): Account credential.
  - `password` (str): Account password.
  - `platform` (Platform): Target platform enum value.
  - `profile_key` (str): Key identifying the browser profile context.
- **Return Type**: `Generator[dict[str, Any], None, None]`
  - Yields dictionaries with updates:
    - Log updates: `{"type": "log", "message": "Step detail..."}`
    - Result updates: `{"type": "result", "status": "đã đăng nhập", "logs": "Full execution log"}`

## Callers
- `backend_presentation.api.run_account_login` endpoint.

## Dependencies (interfaces consumed)
- `BrowserContextManager` (to obtain the page execution instance).
- `AccountRepository` & `LoginHistoryRepository` (to persist execution logs and outcome states).

## Side Effects
- Spawns background Chromium/Chrome processes.
- Communicates with GemLogin REST API to start/stop profiles.
- Writes diagnostic screenshots to disk on failure.
- Writes history records to PostgreSQL.

## Error Handling Summary
- If an uncaught Exception occurs during browser operations, the exception is caught in the context manager or service, an error screenshot is taken, the browser is closed cleanly, and the status of the account is set to `dead` or `checkpoint` (depending on the page content matches).

## Concurrency Notes
- Since Playwright is asynchronous, its service wrapper (`PlaywrightService`) runs inside an async event loop.
- Since DrissionPage is synchronous, its service wrapper (`DrissionPageService`) is invoked using thread pooling wrappers (e.g. `run_in_executor`) in the presentation layer to prevent blocking FastAPI's ASGI event loop.
