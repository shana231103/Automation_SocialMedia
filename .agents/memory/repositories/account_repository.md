# Repository: AccountRepository & LoginHistoryRepository

## Ownership
- `backend_infrastructure` holds concrete SQLAlchemy mappings and operations.
- `backend_domain` defines repository interface signatures.

## Tables or Collections
- `accounts`: Stores accounts data.
- `login_histories`: Stores audit history execution logs.

## Storage Backend
- **PostgreSQL**: Relational database storing accounts and histories.

## Key Queries (plain language)
- Get Account by ID.
- Get All Accounts.
- Save/Update Account (inserts or updates fields like status and last_checked_at).
- Delete Account.
- Save Login History (creates a new audit record for execution log history).
- Get Login Histories by Account ID (chronological lists).
- Clear All Login Histories.

## Adapters
- `SQLAlchemyAccountRepository`
- `SQLAlchemyLoginHistoryRepository`

## Transaction Notes
- Uses SQLAlchemy session scoping (`db.commit()` and `db.rollback()`) to ensure atomic database writes and clean connections management.

## Caching Strategy
- None (Direct relational queries since accounts lists are dynamic and write-heavy).
