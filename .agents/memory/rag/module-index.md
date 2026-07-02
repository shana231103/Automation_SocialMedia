# Module Index

| Module | Path | Purpose | Dependencies |
|--------|------|---------|--------------|
| `backend_domain` | `backend/app/domain` | Contains the core models, platform definitions, and repository interfaces. | None |
| `backend_application` | `backend/app/application` | Declares automation runner contracts and logging proxies. | `backend_domain` |
| `backend_infrastructure` | `backend/app/infrastructure` | Adapters for databases, GemLogin controllers, and selenium-like browser automators. | `backend_domain`, `backend_application` |
| `backend_presentation` | `backend/app/presentation` | Exposes FastAPI controllers and data schemas. | `backend_domain`, `backend_application`, `backend_infrastructure` |
| `frontend` | `frontend` | Single Page Vue 3 Dashboard Interface. | None |
