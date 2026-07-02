# Module: backend_infrastructure

## Purpose
The `backend_infrastructure` module contains the concrete implementations of database models, SQL connections, repository patterns, and browser automation drivers (both DrissionPage and Playwright).

## Public Interfaces
- **`AutomationPage` (ABC)**: Abstract interface for driver-agnostic browser page interactions.
- **`AutomationElement` (ABC)**: Abstract interface for driver-agnostic DOM element interactions.

## Services
- **`DrissionPageAutomationService`**: Wraps ChromiumPage with `DrissionPageWrapper` and dispatches dynamic execution requests to registered actions.
- **`PlaywrightAutomationService`**: Wraps Playwright Page with `PlaywrightPageWrapper` and dispatches dynamic execution requests to registered actions.

## Action Registry & Commands
- **`ACTION_REGISTRY`**: Registry mapping action names to concrete `AutomationAction` implementations.
- **`LoginAction`**: Encapsulates login flows across Facebook, YouTube, TikTok, and Twitter platforms, depending solely on the `AutomationPage` abstraction.

## Repositories
- **`SQLAlchemyAccountRepository`**: Saves, updates, reads, and deletes social accounts from PostgreSQL using SQLAlchemy.
- **`SQLAlchemyLoginHistoryRepository`**: Manages log histories.

## DTOs & Entities
- **`AccountDB`**: SQLAlchemy model mapping to the `accounts` database table.
- **`LoginHistoryDB`**: SQLAlchemy model mapping to the `login_histories` database table.

## Internal Dependencies
- `backend_domain` (implements models and interfaces)
- `backend_application` (implements service interfaces)

## External Dependencies
- **SQLAlchemy / PostgreSQL**: For database connections.
- **DrissionPage**: For synchronous browser control.
- **Playwright**: For asynchronous browser control.
- **Requests**: For communication with the GemLogin profile REST API.

## Callers
- `backend_presentation` (resolves database connection engines and injects concrete services)

## Related Tests
- Integration tests in `backend/test_automation.py` evaluating browser session launches.
- Unit tests in `backend/tests/unit/automation/test_page_wrapper.py`, `test_platforms_facebook.py`, and `test_action_registry.py`.

## Extension Points
- New browser classes can be added in `backend/app/infrastructure/automation/` (e.g. GoLogin support) by extending `BrowserContextManager`.
- New browser automation features (e.g. posting, scraping) can be added as class strategies by inheriting from `AutomationAction` and registering them inside `ACTION_REGISTRY`.

## What MUST NOT Change
- Port-binding configurations and REST API endpoint paths for GemLogin profile control (`/api/profiles/start` and `/api/profiles/stop`).

