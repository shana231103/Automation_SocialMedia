# Module: backend_domain

## Purpose
The `backend_domain` module contains the central domain entities and enums for the system. It describes social accounts and login histories. This layer contains no references to external databases, API routing engines, or browser automation SDKs, serving as the pure core of the application.

## Public Interfaces
- **`AccountRepository`**: Interface definition for reading and persisting `Account` domain entities.
- **`LoginHistoryRepository`**: Interface definition for logging history updates.

## Services
N/A (Business logic is encapsulated directly inside domain model mutators or in application services).

## Repositories
N/A (The repository interfaces reside here, but their implementations are located in `backend_infrastructure`).

## DTOs & Entities
- **`Account`**: Represents a credentials container and status for a social media page.
  - `id`: Optional unique identifier.
  - `username`: Account login.
  - `password`: Account password.
  - `platform`: Target network (from `Platform` enum).
  - `status`: Login state (from `LoginStatus` enum).
  - `last_checked_at`: Timestamp of last verify session.
- **`LoginHistory`**: Represents an audit history log of execution attempts.
  - `id`: Unique record identifier.
  - `account_id`: Foreign key reference to `Account`.
  - `platform`: Target network.
  - `status`: Outcome status.
  - `run_logs`: Text blob containing execution progress logs.
- **`Platform`**: Enum containing `facebook`, `youtube`, `tiktok`, and `twitter`.
- **`LoginStatus`**: Enum containing `đã đăng nhập` (logged in), `chưa đăng nhập` (logged out), `checkpoint`, and `dead`.

## Internal Dependencies
None.

## External Dependencies
Standard Python datetime and typing libraries.

## Callers
- `backend_application`
- `backend_infrastructure`
- `backend_presentation`

## Related Tests
- Unit tests verifying model state transitions (e.g. `Account.update_status`).

## Extension Points
- Can add more platforms to the `Platform` enum without changing database tables or automation driver logic.

## What MUST NOT Change
- Naming of fields in domain objects must remain consistent as they are mapped directly to SQL schemes and presentation JSONs.
