# Data Model: Web Admin Dashboard (005)

## Existing Tables (read + write via new admin API)

### appointments
| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| patient_user_id | UUID FK → telegram_users.id | |
| dentist_id | UUID FK → dentists.id | |
| slot_date | DATE | |
| start_time | TIME | |
| end_time | TIME | |
| reason | VARCHAR(150) | |
| status | ENUM(confirmed, cancelled) | admin can change to cancelled |
| google_event_id | VARCHAR | used to cancel Google Calendar event |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

**Admin operations**: list (with JOIN to telegram_users + dentists), get by id, cancel (status → cancelled), delete.

### dentists
| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| name | VARCHAR(100) UNIQUE | |
| calendar_id | VARCHAR(255) UNIQUE | Google Calendar identifier |
| active_status | BOOLEAN | false = hidden from bot |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

**Admin operations**: list, get by id, create, update (name / calendar_id / active_status), soft-delete via active_status=false.

### telegram_users
| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| telegram_user_id | BIGINT UNIQUE | |
| first_name | VARCHAR | |
| last_name | VARCHAR | nullable |
| username | VARCHAR | nullable |
| is_active | BOOLEAN | |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

**Admin operations**: list (read-only), get by id with linked appointments.

## New Table

### admin_users
| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK DEFAULT gen_random_uuid() | |
| username | VARCHAR(50) NOT NULL UNIQUE | |
| hashed_password | VARCHAR(255) NOT NULL | bcrypt cost ≥ 12 |
| is_active | BOOLEAN NOT NULL DEFAULT TRUE | |
| created_at | TIMESTAMP NOT NULL DEFAULT NOW() | |
| last_login_at | TIMESTAMP | nullable |

**Migration**: `migrations/versions/006_add_admin_users.py`  
**Seeding**: `scripts/seed_admin.py --username admin --password <secret>`

## State Transitions

### Appointment status
```
confirmed ──(admin cancel)──→ cancelled
confirmed or cancelled ──(admin delete)──→ [row removed]
```

### Dentist active_status
```
true ──(admin deactivate)──→ false
false ──(admin reactivate)──→ true
```

## Validation Rules

- Dentist `name`: non-empty, max 100 chars, unique.
- Dentist `calendar_id`: non-empty, max 255 chars, unique.
- AdminUser `username`: non-empty, max 50 chars, alphanumeric + underscore.
- AdminUser `password` (at creation): min 12 chars.
- Appointment cancel: only allowed when `status == confirmed`.
- Appointment delete: allowed regardless of status (with confirmation).
