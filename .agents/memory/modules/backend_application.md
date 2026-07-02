# Module: backend_application

## Purpose
The `backend_application` module defines the abstract workflow interfaces and orchestration adapters of the backend service. It bridges domain abstractions with concrete infrastructure implementations.

## Public Interfaces
- **`BrowserContextManager`**: Interface defining context execution hooks (`__enter__` and `__exit__`) and retrieval of current logs via `get_new_logs()`.
- **`AutomationService`**: Interface defining automation capabilities like `run_login()`.

## Services
N/A (Business workflows are declared via implementations of `AutomationService` inside infrastructure).

## Repositories
N/A (Relies on repositories injected into interfaces).

## DTOs & Entities
N/A (Imports models and entities from `backend_domain`).

## Internal Dependencies
- `backend_domain` (for data structures and domain definitions)

## External Dependencies
- Standard library typing and helper tools.

## Callers
- `backend_presentation` (for invoking use cases)
- `backend_infrastructure` (for implementation classes)

## Related Tests
- Mocks of `BrowserContextManager` and `AutomationService` inside unit tests.

## Extension Points
- Implementations of `AutomationService` can be written for new automation frameworks (e.g. Selenium) by adhering to the returned generator format.

## What MUST NOT Change
- The method signatures of `run_login()` and `BrowserContextManager` must not be altered, as they form the interface boundary for the API presentation layer.
