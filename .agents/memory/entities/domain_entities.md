# Entities: domain_entities

## Entity: Account
Represents a social account configuration profile.
- **Fields**:
  - `id` (int, optional): Unique ID.
  - `username` (str): Account credential login (email/phone/username).
  - `password` (str): Account credential password.
  - `platform` (Platform): Target platform network (Facebook, YouTube, TikTok, Twitter).
  - `status` (LoginStatus): Execution login state.
  - `last_checked_at` (datetime, optional): Timestamp of last verification run.
- **Validation Rules**:
  - `username` and `password` must not be empty.
- **Mutability**:
  - `status` and `last_checked_at` are mutable and updated via the `update_status` method.

## Entity: LoginHistory
Audit log entry representing a single automation login run.
- **Fields**:
  - `id` (int, optional): Log entry ID.
  - `account_id` (int): Account reference.
  - `platform` (Platform): Platform executed.
  - `status` (LoginStatus): Result status of the run.
  - `run_logs` (str): Content of the runtime step log block.
  - `created_at` (datetime): Entry creation timestamp.

## Enum: Platform
- **Values**:
  - `facebook`: Facebook automation target.
  - `youtube`: YouTube automation target.
  - `tiktok`: TikTok automation target.
  - `twitter`: Twitter (X) automation target.

## Enum: LoginStatus
- **Values**:
  - `đã đăng nhập`: User is confirmed logged in.
  - `chưa đăng nhập`: User is not logged in.
  - `checkpoint`: Account triggered verification checkpoint block.
  - `dead`: Account is disabled or locked.
