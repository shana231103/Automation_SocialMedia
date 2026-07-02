# Module: backend_presentation

## Purpose
The `backend_presentation` module acts as the delivery mechanism for the backend, exposing FastAPI REST API endpoints, managing CORS policies, parsing incoming request schemas, and streaming SSE logs.

## Public Interfaces
None (serves as the API entrypoint of the backend application).

## Services
N/A.

## Repositories
Resolves DB Sessions using SQLAlchemy sessionmaker dependency injection (`get_db`).

## DTOs & Entities (FastAPI Schemas)
- `AccountCreate`, `AccountResponse`, `AccountUpdate`
- `LoginRequest`, `LoginHistoryResponse`

## Internal Dependencies
- `backend_domain` (mappings to enums)
- `backend_application` (triggers automation flows)
- `backend_infrastructure` (instantiates repositories and injects services)

## External Dependencies
- **FastAPI**: REST API frameworks.
- **Pydantic**: Data schema validation.
- **Uvicorn**: ASGI web server runner.

## Callers
- External clients (e.g. frontend Vue application).

## Related Tests
- API route integration tests.

## Extension Points
- Can add more endpoints to `app/presentation/api.py` as more automation features (like cookies exporting or bulk page creation) are added.

## What MUST NOT Change
- SSE format expectations (`event: log` vs `event: result`) which are consumed by the frontend state managers.
