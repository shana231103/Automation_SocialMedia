# Project Summary

## Project Name
Automation Social Media

## Business Domain & Purpose
The Automation Social Media project is a web-based, multi-platform solution designed to automate social account login and verification routines across mainstream social media networks (including Facebook, YouTube, TikTok, and Twitter). The system's primary commercial/operational purpose is to manage a large portfolio of social profiles securely, validating their credential states, performing automated tasks, and diagnosing connection issues (like checkpoint verification or account death). It integrates with both default local web browsers and advanced antidetect browsers (like GemLogin and GoLogin) to handle cookie isolation and proxy routing, mimicking organic user behavior.

## Primary Language
Python (v3.11/v3.14) is used for the entire backend application, including web server routing, database queries, and browser process execution.

## Secondary Languages
JavaScript (Vue 3, Vite, TailwindCSS v4) is used for the frontend application to construct the dashboard, management views, and live execution consoles.

## Frameworks & Libraries (with versions)
- **FastAPI (v0.100+)**: Fast and lightweight web framework for building REST APIs with automatic documentation.
- **SQLAlchemy (v2.0+)**: Relational Database Mapper utilized to orchestrate database entities and transactions.
- **PostgreSQL**: Robust, enterprise-grade relational database storing accounts and log records.
- **DrissionPage (v4.0+)**: Python browser automation library that integrates Chromium control and requests.
- **Playwright (v1.40+)**: Async multi-browser automation framework used to connect to antidetect browsers via CDP protocols.
- **Vue 3 (v3.5+)**: Progressively-adoptable JavaScript framework for building user interfaces.
- **Vite (v8.0+)**: Next-generation frontend build tool.
- **TailwindCSS (v4.3+)**: Utility-first CSS styling framework.

## Architecture Style
The backend is structured around Domain-Driven Design (DDD) principles combined with a Clean Architecture / Hexagonal layout:
- **Domain Layer (`backend/app/domain`)**: Declares standard entities, enums, and repository contract interfaces, defining core model concepts completely decoupled from SQL dialects, REST APIs, or browser engines.
- **Application Layer (`backend/app/application`)**: Declares abstract workflows and ports (such as `BrowserContextManager` and `AutomationService`). Coordinates calls between domain models and infrastructure adapters.
- **Infrastructure Layer (`backend/app/infrastructure`)**: Implements database interactions using SQLAlchemy/PostgreSQL and browser integrations (Playwright and DrissionPage adapters, GemLogin controllers).
- **Presentation Layer (`backend/app/presentation`)**: Exposes REST endpoints, validates request schemas via Pydantic, and implements event loops for Server-Sent Events (SSE).

## Dependency Injection Pattern
Dependency Injection (DI) is implemented via configuration patterns and class decorators:
- The system checks the environment variable `AUTOMATION_PROVIDER` (`playwright` or `drissionpage`) to load the corresponding concrete service subclass.
- Database sessions are injected dynamically into FastAPI routes using the standard dependency injection container (`Depends(get_db)`).

## Main Modules
1. **backend_domain** (`backend/app/domain`)
   - `models.py`: Defines business concepts like `Account` and `LoginHistory` and mutator rules.
   - `repositories.py`: Specifies repository interfaces for database access.
2. **backend_application** (`backend/app/application`)
   - `interfaces.py`: Declares driver connection managers and logging ports.
3. **backend_infrastructure** (`backend/app/infrastructure`)
   - `database/connection.py`: Connects PostgreSQL server.
   - `database/models.py`: Sets up SQLAlchemy DB entities.
   - `database/repositories.py`: Concrete SQL databases implementations.
   - `automation/gemlogin_browser.py`: Starts GemLogin profiles.
   - `automation/local_browser.py`: Launches local Chrome instances.
   - `automation/playwright_browser.py`: Sets up Playwright sessions.
   - `automation/drission_page.py`: Automates interactions via DrissionPage.
   - `automation/playwright_service.py`: Automates interactions via Playwright.
4. **backend_presentation** (`backend/app/presentation`)
   - `api.py`: FastAPI endpoints and SSE generators.
   - `schemas.py`: Pydantic input/output converters.
5. **frontend** (`frontend/src`)
   - Dashboard views, account lists, API client wrappers, and real-time console streamers.

## Databases & Storage Backends
- **PostgreSQL**: Primary SQL store containing tables for accounts and audit login history.

## Configuration & Environment Files
- **`.env` / `.env.example`**: System configurations (e.g. database credentials, antidetect browser endpoints, active automation provider).
- **`Makefile`**: Practical build and testing utility runner containing targets to run tests, start dev servers, and clean environment profiles.
- **`.ovpn` Profiles**: OpenVPN connection profiles, used to route traffic through secure VPN networks during browser automation sessions.

## External Services & Integrations
- **GemLogin Browser REST API**: Runs on localhost port 1010 (`/api/profiles/start` and `/api/profiles/stop`) to start and stop antidetect browser profiles, passing remote debugger websocket endpoints.

## Build Commands
- **Backend Setup**:
  - Setup virtual env: `python -m venv .venv`
  - Install dependencies: `pip install -r requirements.txt`
  - Run database creation: `python create_db.py`
  - Run command scripts: defined in `Makefile`
- **Frontend Setup**:
  - Install packages: `npm install`
  - Run development server: `npm run dev`
  - Compile package: `npm run build`


## Test Commands
- **Unit Tests**:
  `python -m unittest discover -s backend`
- **Integration Tests**:
  `python backend/test_automation.py`
- **Makefile wrappers**:
  - `make test`: Run unittest runner.
  - `make test-integration`: Run live integration test suite.

## Deployment Method
- **Docker**: Containerization using `Dockerfile` and multi-service orchestration via `docker-compose.yml`.
- **FastAPI / Uvicorn Server**: Runs in production via Uvicorn listener on specific ports.

## Coding Conventions
- **Clean Architecture isolation**: No database libraries (like SQLAlchemy models) or automation modules (like Playwright contexts) should be accessed directly inside domain entities.
- **Context managers**: Every driver class must be structured as a context manager (`__enter__` and `__exit__`), ensuring resources are disposed of correctly even in the event of unforeseen exceptions.
- **Logging**: Stream detailed steps to a custom list of logs that can be polled or streamed using Server-Sent Events (SSE).
- **Log formats**: Yield data in standard JSON wrappers matching API presentation models.

## Naming Conventions
- **Variables / Functions**: snake_case (e.g. `run_login`, `account_id`).
- **Classes**: PascalCase (e.g. `AccountRepository`, `GemLoginBrowser`).
- **Database Tables**: Plural lowercase (e.g. `accounts`, `login_histories`).
- **Frontend Components**: PascalCase for files, kebab-case for tags.

## File Size Constraints
- Avoid monolithic service files. Files under `infrastructure/automation` should be kept below 500 lines.
- Entities and models should stay cohesive, ideally below 200 lines.

## Key Design Principles
1. **Driver Interoperability**: Swapping browser engines from Playwright to DrissionPage should require zero modifications to domain or application rules.
2. **Context Cleanup Safety**: Prevent zombie browser processes by using standard `__exit__` blocks that trigger cleanup logic even during sudden cancellations or database dropouts.
3. **SSE Real-Time Feedback**: Streaming live steps directly to the frontend Vue components to keep users updated on background login procedures.
4. **Proxy Isolation**: Routing all automated traffic through the proxy settings assigned to antidetect profiles.

## Known Anti-Patterns to Avoid
- **Raw API calls in presentation layer**: High coupling of browser automation logic to REST controllers prevents independent testing.
- **Manual process killing**: Avoid sweeping commands like `pkill chrome` which may target the host user's personal web browser sessions.
- **No db transaction scopes**: Running database updates without commit/rollback wrappers, leading to connections leaking.

## Workflow Mechanics: Real-Time Login Stream
When a user clicks "Login" on the frontend:
1. The frontend initiates an EventSource connection to `/api/accounts/{id}/login/stream`.
2. FastAPI processes the request, starts a database session, and queries the target account credentials.
3. The server checks the `AUTOMATION_PROVIDER` configuration to select `PlaywrightService` or `DrissionPageService`.
4. The service initializes the appropriate `BrowserContextManager` wrapper class (e.g. `PlaywrightBrowser` or `GemLoginBrowser`).
5. The wrapper contacts the local GemLogin API to launch the profile and fetch the debugger address.
6. The driver attaches to the debugger address and returns a Page control instance.
7. The automation script executes login steps, yielding progress messages like "Entering username...", "Submitting credentials...", etc.
8. These messages are serialized and streamed to the client as Server-Sent Events.
9. On success or failure, the browser context exits, capturing a screenshot if a failure occurred.
10. The result is logged into the `login_histories` database table, the account status is updated, and the final state is streamed to the user interface.

## Memory Generated At
2026-07-03T05:30:30+07:00

## Memory Version
1.0.0
