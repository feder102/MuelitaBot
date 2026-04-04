# Data Model: Telegram Webhook Menu Backend

**Version**: 1.0.0
**Created**: 2026-04-04
**Purpose**: Define database schema and entity relationships for webhook menu system

---

## Overview

The data model supports:
- Persistent user profiles (Telegram user metadata)
- Conversation state tracking (current menu state per user)
- Audit logging (immutable record of all interactions for compliance)
- Extensibility (future menu options, flow transitions)

---

## Entity: TelegramUser

Represents a Telegram user who has interacted with the bot.

### Fields

| Field | Type | Constraints | Purpose |
|-------|------|-----------|---------|
| id | UUID | PRIMARY KEY | Internal unique identifier |
| telegram_user_id | BIGINT | UNIQUE, NOT NULL | Telegram's user ID (from API) |
| first_name | VARCHAR(255) | NOT NULL | User's first name (from Telegram) |
| last_name | VARCHAR(255) | NULLABLE | User's last name (from Telegram) |
| username | VARCHAR(255) | NULLABLE, UNIQUE | Telegram handle (if set) |
| is_active | BOOLEAN | NOT NULL, DEFAULT TRUE | Soft delete flag (privacy: don't hard delete PHI) |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Account creation date (UTC) |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Last modification date (UTC) |

### Validation Rules

- `telegram_user_id`: > 0 (Telegram constraint)
- `first_name`: not empty, max 255 chars
- `last_name`: optional, max 255 chars
- `username`: optional, alphanumeric + underscore, max 32 chars
- `is_active`: only inactive users can have their data purged after retention period

### Relationships

- **ConversationState**: 1:1 (each user has one active conversation state)
- **AuditLog**: 1:M (each user has many audit log entries)

### Indexes

- `(telegram_user_id)` - UNIQUE: Quick lookup by Telegram ID
- `(created_at DESC)` - List users by join date
- `(is_active, updated_at DESC)` - Find active users recently active (for retention cleanup)

### Notes

- Never hard delete users (medical data retention compliance)
- Mark as inactive instead; implement retention policy to purge after X days
- `telegram_user_id` is immutable; if user changes username, `username` field updates but `telegram_user_id` stays same

---

## Entity: ConversationState

Tracks the current state of a user's interaction with the bot.

### Fields

| Field | Type | Constraints | Purpose |
|-------|------|-----------|---------|
| user_id | UUID | PRIMARY KEY, FK → TelegramUser.id | Reference to user |
| current_state | ENUM | NOT NULL, DEFAULT 'AWAITING_MENU' | Current state in conversation flow |
| last_interaction | TIMESTAMP | NOT NULL, DEFAULT NOW() | When user last sent/received message (UTC) |
| menu_display_count | INTEGER | NOT NULL, DEFAULT 0 | How many times menu has been shown (UX metric) |
| metadata | JSONB | NULLABLE, DEFAULT '{}' | Extensible data (future: selected preferences, temp data) |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | State created date (UTC) |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | State last modified date (UTC) |

### State Machine

```
AWAITING_MENU
  └─ User sends initial message or re-initiates
  
AWAITING_SELECTION
  └─ Menu displayed; waiting for "1" or "2"
  
APPOINTMENT_SELECTED
  └─ User selected "1: Solicitar turno"
  └─ Handoff to appointment booking flow
  └─ Cleanup: Mark state as COMPLETED after flow done
  
SECRETARY_SELECTED
  └─ User selected "2: Hablar con secretaria"
  └─ Handoff to secretary chat flow
  └─ Cleanup: Mark state as COMPLETED after flow done
  
COMPLETED
  └─ Conversation finished (appointment booked or secretary chat ended)
  
INACTIVE
  └─ User hasn't interacted in > 30 days; can be purged with user
```

### Enum Definition (SQL)

```sql
CREATE TYPE conversation_state_enum AS ENUM (
  'AWAITING_MENU',
  'AWAITING_SELECTION',
  'APPOINTMENT_SELECTED',
  'SECRETARY_SELECTED',
  'COMPLETED',
  'INACTIVE'
);
```

### Validation Rules

- `user_id`: must exist in TelegramUser table (FK constraint)
- `current_state`: must be one of the defined enum values
- `last_interaction`: must be ≤ now() (past timestamp)
- `menu_display_count`: ≥ 0 (cannot be negative)
- `metadata`: valid JSON object (Postgres constraint)

### Relationships

- **TelegramUser**: M:1 (many states → one user, but only active state per user due to PRIMARY KEY)

### Indexes

- `(current_state, last_interaction DESC)` - Find users in specific state, ordered by recent activity
- `(last_interaction DESC)` - Activity tracking / cleanup queries

### Metadata Schema (JSONB)

```json
{
  "menu_option_selected": "1",        // Future: track which option user selected
  "last_menu_option_at": "2026-04-04T10:30:00Z",  // Timestamp of last selection
  "temp_data": {}                     // For future appointment/secretary flows to store temp data
}
```

### Notes

- Only one ConversationState row per user (PRIMARY KEY = user_id)
- `last_interaction` auto-updates on every message received/sent (update via trigger or ORM)
- Soft-delete at user level (ConversationState inherits via FK cascade)

---

## Entity: AuditLog

Immutable record of all user interactions for compliance and debugging.

### Fields

| Field | Type | Constraints | Purpose |
|-------|------|-----------|---------|
| id | UUID | PRIMARY KEY | Unique log entry ID |
| user_id | UUID | NULLABLE, FK → TelegramUser.id | Who performed the action (null if auth failed) |
| action | VARCHAR(50) | NOT NULL | Type of action (enum-like) |
| status | ENUM | NOT NULL | Outcome (SUCCESS, VALIDATION_FAILED, ERROR) |
| message_text | TEXT | NULLABLE | User's input message (stored for audit) |
| response_text | TEXT | NULLABLE | Bot's response message (stored for audit) |
| error_detail | TEXT | NULLABLE | If status=ERROR, error message/stack (server-side only) |
| ip_address | INET | NULLABLE | Source IP (from X-Forwarded-For or RemoteAddr) |
| request_headers | JSONB | NULLABLE | Selected headers for security audit (User-Agent, etc.) |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | When action occurred (UTC) |

### Action Types

| Action | Trigger | Example |
|--------|---------|---------|
| WEBHOOK_RECEIVED | Webhook arrives at /webhook | Valid Update from Telegram |
| SIGNATURE_VALIDATION_FAILED | Invalid X-Telegram-Bot-API-Secret-SHA256 | Spoofed request rejected |
| MESSAGE_PARSED | Message successfully extracted | "Hola" from user 12345 |
| MENU_DISPLAYED | Menu sent to user | "1: Solicitar turno, 2: Hablar con secretaria" |
| MENU_SELECTION_MADE | User selected option | Selection "1" recognized |
| APPOINTMENT_ROUTED | Appointment flow initiated | Handoff to appointment module |
| SECRETARY_ROUTED | Secretary flow initiated | Handoff to secretary module |
| INVALID_SELECTION | User sent non-matching text | "help" doesn't match menu |
| DATABASE_ERROR | DB operation failed | Connection pool exhausted |
| TELEGRAM_API_ERROR | Sending response failed | Rate limited by Telegram |

### Status Enum

```sql
CREATE TYPE audit_status_enum AS ENUM (
  'SUCCESS',
  'VALIDATION_FAILED',
  'ERROR'
);
```

### Validation Rules

- `user_id`: nullable (failed auth logs don't have user_id)
- `action`: one of predefined action strings (validate in application)
- `status`: one of enum values
- `message_text`: max 4096 chars (Telegram limit)
- `response_text`: max 4096 chars (Telegram limit)
- `error_detail`: max 10000 chars (don't store stack traces, summarize)
- `ip_address`: valid IPv4 or IPv6
- `created_at`: immutable, set at insert time

### Relationships

- **TelegramUser**: M:1 (many audit logs → one user)

### Indexes

- `(user_id, created_at DESC)` - Retrieve user's action history
- `(action, status, created_at DESC)` - Find specific action types and outcomes
- `(created_at DESC)` - Time-based queries (last 24h, etc.)
- `(status) WHERE status != 'SUCCESS'` - Quick find of errors for investigation

### Retention Policy

- Keep audit logs indefinitely (medical compliance)
- Optional: Archive to cold storage after 1 year
- Never delete (immutable by design)

### Notes

- **Immutable**: Only INSERT allowed; no UPDATE/DELETE (enforced via PG permissions if needed)
- **PHI consideration**: message_text and response_text may contain appointment details; ensure DB access is restricted
- **Server-side only**: error_detail is never sent to client (prevents info leakage)
- **Trigger for timestamp**: Optional: use PG trigger to auto-update `created_at` (but usually app sets it)

---

## Migration Strategy

### Initial Migration (v001)

```sql
-- Create enums
CREATE TYPE conversation_state_enum AS ENUM (...);
CREATE TYPE audit_status_enum AS ENUM (...);

-- Create tables
CREATE TABLE telegram_users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  telegram_user_id BIGINT UNIQUE NOT NULL,
  first_name VARCHAR(255) NOT NULL,
  last_name VARCHAR(255),
  username VARCHAR(255) UNIQUE,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
  CHECK (telegram_user_id > 0)
);

CREATE TABLE conversation_state (
  user_id UUID PRIMARY KEY REFERENCES telegram_users(id) ON DELETE CASCADE,
  current_state conversation_state_enum NOT NULL DEFAULT 'AWAITING_MENU',
  last_interaction TIMESTAMP NOT NULL DEFAULT NOW(),
  menu_display_count INTEGER NOT NULL DEFAULT 0 CHECK (menu_display_count >= 0),
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES telegram_users(id) ON DELETE SET NULL,
  action VARCHAR(50) NOT NULL,
  status audit_status_enum NOT NULL,
  message_text TEXT,
  response_text TEXT,
  error_detail TEXT,
  ip_address INET,
  request_headers JSONB,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_telegram_users_active ON telegram_users(is_active, updated_at DESC);
CREATE INDEX idx_conversation_state_activity ON conversation_state(current_state, last_interaction DESC);
CREATE INDEX idx_audit_log_user_time ON audit_log(user_id, created_at DESC);
CREATE INDEX idx_audit_log_action ON audit_log(action, status, created_at DESC);
CREATE INDEX idx_audit_log_errors ON audit_log(status) WHERE status != 'SUCCESS';
```

### Rollback Procedure

Downtime: ~1 minute (table locks are brief for dropping tables)

```sql
DROP TABLE audit_log;
DROP TABLE conversation_state;
DROP TABLE telegram_users;
DROP TYPE conversation_state_enum;
DROP TYPE audit_status_enum;
```

### Future Migrations

- **v002**: Add message table for message deduplication / pagination
- **v003**: Add user preferences table (doctor selection, language, etc.)
- **v004**: Add appointments table (integration with appointment booking)

---

## Data Integrity Constraints

### Foreign Keys

- `conversation_state.user_id` → `telegram_users.id` (ON DELETE CASCADE)
- `audit_log.user_id` → `telegram_users.id` (ON DELETE SET NULL)

### Unique Constraints

- `telegram_users.telegram_user_id` (UNIQUE)
- `telegram_users.username` (UNIQUE, NULLABLE)
- `conversation_state.user_id` (PRIMARY KEY = one state per user)

### Check Constraints

- `telegram_users.telegram_user_id > 0`
- `conversation_state.menu_display_count >= 0`

---

## Example Queries

### Find user's current state
```sql
SELECT cs.current_state, cs.last_interaction, tu.first_name
FROM conversation_state cs
JOIN telegram_users tu ON cs.user_id = tu.id
WHERE tu.telegram_user_id = $1;
```

### Audit trail for user (last 24h)
```sql
SELECT action, status, message_text, created_at
FROM audit_log
WHERE user_id = $1 AND created_at > NOW() - INTERVAL '24 hours'
ORDER BY created_at DESC;
```

### Find errors in last hour
```sql
SELECT user_id, action, error_detail, created_at
FROM audit_log
WHERE status = 'ERROR' AND created_at > NOW() - INTERVAL '1 hour'
ORDER BY created_at DESC;
```

### Inactive users (for data deletion policy)
```sql
SELECT tu.id, tu.telegram_user_id, tu.first_name, cs.last_interaction
FROM telegram_users tu
LEFT JOIN conversation_state cs ON tu.id = cs.user_id
WHERE tu.is_active = TRUE 
  AND cs.last_interaction < NOW() - INTERVAL '30 days'
ORDER BY cs.last_interaction ASC;
```

---

## Design Notes

- **Immutability**: AuditLog is append-only (audit trail compliance)
- **Soft deletes**: Users marked inactive, not deleted (data retention for legal holds)
- **JSONB metadata**: Allows future extensibility without schema migrations
- **UTC timestamps**: All times in UTC for consistency across timezones
- **No sensitive data in logs**: message_text and response_text are trimmed to avoid storing full conversation (optional: encrypt if needed)
- **Stateless application**: State persisted in DB, not in memory (allows horizontal scaling)
