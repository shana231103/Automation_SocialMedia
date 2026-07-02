# API Group: accounts_api

## Protocol
REST (JSON) and Server-Sent Events (SSE) for log streaming.

## Base Path or Namespace
`/api`

## Ownership
- `backend_presentation.api`

## Authentication Required
None (For local/intranet automation workspace deployment).

---

### GET `/api/accounts`
- **Purpose**: Get all social accounts registered in the system.
- **Request**: None.
- **Response**: List of `AccountResponse` JSON objects.
- **Auth**: None.

### POST `/api/accounts`
- **Purpose**: Create a new social account profile.
- **Request**: `AccountCreate` JSON body containing username, password, and platform.
- **Response**: Created `AccountResponse` object.
- **Auth**: None.

### PUT `/api/accounts/{id}`
- **Purpose**: Update an account's details.
- **Request**: `AccountUpdate` JSON body.
- **Response**: Updated `AccountResponse` object.
- **Auth**: None.

### DELETE `/api/accounts/{id}`
- **Purpose**: Remove an account from the system.
- **Request**: ID in path parameter.
- **Response**: Success status.
- **Auth**: None.

### GET `/api/accounts/{id}/login/stream`
- **Purpose**: Triggers the login automation flow for a given account and streams real-time execution logs back to the caller using Server-Sent Events (SSE).
- **Request**: Account ID in path. Query parameters: `profile_key` (optional).
- **Response**: SSE text stream (`text/event-stream`).
  - Yields chunks of events:
    - `event: log\ndata: {"message": "Step description"}\n\n`
    - `event: result\ndata: {"status": "đã đăng nhập", "logs": "..."}\n\n`
- **Auth**: None.

### GET `/api/accounts/{id}/history`
- **Purpose**: Retrieve historical login records and logs for a specific account.
- **Request**: Account ID in path.
- **Response**: List of `LoginHistoryResponse` objects.
- **Auth**: None.

### DELETE `/api/history`
- **Purpose**: Clear all history logs.
- **Request**: None.
- **Response**: Success status.
- **Auth**: None.
