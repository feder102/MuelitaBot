# Data Model: Multi-Dentist Appointment Booking

**Feature**: 003-multi-dentist-booking | **Date**: 2026-04-05

## Overview

This document defines the data entities, relationships, and constraints for multi-dentist support. All changes are **additive** and maintain backward compatibility.

---

## Core Entities

### 1. Dentist (NEW)

**Purpose**: Represents a dental professional in the system.

**Fields**:
| Field | Type | Constraints | Purpose |
|-------|------|-----------|---------|
| `id` | UUID | PRIMARY KEY | Unique identifier |
| `name` | String(100) | NOT NULL, UNIQUE | Dentist name (e.g., "Hector", "Fulano") |
| `calendar_id` | String(255) | NOT NULL, UNIQUE | Google Calendar ID for this dentist |
| `active_status` | Boolean | NOT NULL, DEFAULT TRUE | Whether dentist is available for bookings |
| `created_at` | DateTime | NOT NULL, DEFAULT utcnow() | Audit: when dentist was added |
| `updated_at` | DateTime | NOT NULL, DEFAULT utcnow(), ON UPDATE utcnow() | Audit: last modification |

**Indexes**:
- `idx_dentist_active_status`: ON (active_status) — for filtering active dentists in booking flow
- `idx_dentist_name`: ON (name) — for dentist lookup by name (future: secretary search)

**Validation Rules**:
- `name`: 1-100 characters, non-empty, must be unique
- `calendar_id`: Valid Google Calendar ID format (typically email or alphanumeric with hyphens)
- `active_status`: Boolean; when FALSE, dentist excluded from booking menu

**Usage Examples**:
```
INSERT INTO dentists (name, calendar_id) 
VALUES ('Hector', 'hector@clinic.calendar.google.com');

SELECT * FROM dentists WHERE active_status = TRUE;
```

---

### 2. Appointment (EXTENDED)

**Current State** (Feature 002):
- `id`, `patient_user_id`, `appointment_date`, `start_time`, `end_time`, `reason`, `status`, timestamps
- Unique constraint: `(appointment_date, start_time)`

**Changes for Multi-Dentist**:

**New Field**:
| Field | Type | Constraints | Purpose |
|-------|------|-----------|---------|
| `dentist_id` | UUID | FOREIGN KEY → dentists.id | Links appointment to specific dentist |

**Updated Constraints**:
- Old: `UNIQUE (appointment_date, start_time)`
- New: `UNIQUE (dentist_id, appointment_date, start_time)` — allows same time slot with different dentists

**Relationships**:
- `appointment.patient_user_id` → `telegram_users.id` (unchanged)
- `appointment.dentist_id` → `dentist.id` (NEW)

**Validation Rules** (new):
- `dentist_id`: Must reference an active dentist at time of booking
- Constraint verified at service layer before appointment creation

**Backward Compatibility**:
- `dentist_id` initially nullable during migration
- Single-dentist clinics: auto-select dentist if only one exists
- Existing appointments: dentist_id assigned based on existing calendar context (semantic preservation)

**Migration Path**:
1. Add column `dentist_id` (nullable)
2. For existing appointments, if applicable, populate with default/placeholder dentist
3. Add foreign key constraint with ON DELETE RESTRICT (prevent dentist deletion if appointments exist)
4. Update uniqueness constraint to include dentist_id

---

### 3. ConversationState (EXTENDED)

**Current State** (Feature 001):
- `id`, `user_id`, `current_step`, `step_context`, `created_at`, `updated_at`
- Tracks conversation flow (menu → option selection → booking steps)

**Changes for Multi-Dentist**:

**New Field** (in step_context JSON):
```python
{
    "current_step": "SELECTING_DENTIST",  # or existing steps
    "selected_dentist_id": "<uuid>",      # UUID of selected dentist
    "selected_appointment": {...},         # existing
    # ... other context
}
```

**Rationale**:
- Reuse existing JSON flexibility of `step_context`
- No schema change; purely data structure extension
- Allows full conversation replay/debugging

**State Transitions**:
```
MENU 
  ↓ (user selects option 1: appointment)
SELECTING_DENTIST (NEW step)
  ↓ (user selects dentist)
[step_context.selected_dentist_id = <uuid>]
WAITING_FOR_APPOINTMENT (existing step, but now with dentist context)
  ↓ (remaining flow identical)
```

---

## Relationships Diagram

```
TelegramUser
    ├── appointments (1-to-many)
    │   └── Dentist (many-to-1)
    │       └── Appointments (1-to-many)
    └── conversation_state
        └── step_context: {selected_dentist_id, ...}

Dentist
    ├── appointments (1-to-many)
    └── audit: created_at, updated_at
```

---

## Schema Changes by Phase

### Phase 1 (Migration Required)

**SQL (Pseudo-code; actual Alembic will generate this)**:

```sql
-- Create dentist table
CREATE TABLE dentists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    calendar_id VARCHAR(255) NOT NULL UNIQUE,
    active_status BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX idx_dentist_active_status ON dentists(active_status);
CREATE INDEX idx_dentist_name ON dentists(name);

-- Alter appointments table
ALTER TABLE appointments
ADD COLUMN dentist_id UUID;

-- Add foreign key constraint (after data migration)
ALTER TABLE appointments
ADD CONSTRAINT fk_appointments_dentist_id
FOREIGN KEY (dentist_id) REFERENCES dentists(id) ON DELETE RESTRICT;

-- Drop old unique constraint and add new one
ALTER TABLE appointments
DROP CONSTRAINT uq_appointment_slot;

ALTER TABLE appointments
ADD CONSTRAINT uq_appointment_slot_per_dentist
UNIQUE (dentist_id, appointment_date, start_time);

CREATE INDEX idx_appointment_dentist_id ON appointments(dentist_id);
```

### Phase 2+ (Future Enhancements)

- **Dentist availability**: Add `working_hours`, `break_times` to Dentist
- **Patient-dentist assignment**: Add `preferred_dentist_id` to TelegramUser
- **Dentist schedule exceptions**: New table for holidays/unavailable dates

---

## Data Integrity & Constraints

| Constraint | Type | Enforcement | Purpose |
|-----------|------|------------|---------|
| Dentist.name UNIQUE | CHECK | Database | Prevent duplicate dentist names |
| Dentist.calendar_id UNIQUE | CHECK | Database | Prevent accidental calendar sharing |
| Appointment.dentist_id FK | FOREIGN KEY | Database | Ensure appointments link to valid dentists |
| Appointment uniqueness | CHECK | Database | Prevent double-booking per dentist |
| Appointment.dentist_id NOT NULL | CHECK | Application (initial), Database (after migration) | Every appointment must have a dentist |

---

## Performance Considerations

**Indexes**:
- `idx_dentist_active_status`: Quick filter for "show available dentists" query
- `idx_dentist_name`: Future: secretary searching for dentist
- `idx_appointment_dentist_id`: Quick lookup of dentist's appointments

**Query Patterns**:
```sql
-- Get active dentists (booking menu)
SELECT * FROM dentists WHERE active_status = TRUE ORDER BY name;

-- Get available slots for specific dentist
SELECT * FROM google_calendar_slots 
WHERE calendar_id = (SELECT calendar_id FROM dentists WHERE id = ?)
AND appointment_date >= CURRENT_DATE;

-- Check if time slot is booked for dentist
SELECT COUNT(*) FROM appointments
WHERE dentist_id = ? 
AND appointment_date = ? 
AND start_time = ?;

-- Get all appointments for dentist (secretary view - future)
SELECT * FROM appointments
WHERE dentist_id = ? AND status != 'CANCELLED'
ORDER BY appointment_date, start_time;
```

---

## Migration Checklist

- [ ] Create Alembic migration file
- [ ] Test migration forward (add tables/columns)
- [ ] Test migration backward (rollback)
- [ ] Handle existing appointment data (assign default/placeholder dentist if needed)
- [ ] Verify foreign key constraints
- [ ] Test query performance with new indexes
- [ ] Document rollback procedure for production incident

---

## Assumptions & Notes

1. **Google Calendar IDs are unique**: Each dentist has exactly one calendar ID; no calendar sharing
2. **Migration timing**: Alembic migration runs before new code deployment (safe to deploy independently)
3. **Backward compatibility**: Old code continues to work; new code gracefully handles missing dentist_id
4. **No data loss**: All existing appointments preserved; dentist_id populated based on context
5. **Scalability**: Schema supports 1000s of dentists without performance issues (simple table; no denormalization)

---

## Related Documentation

- **Functional Requirements**: See [spec.md](spec.md) FR-001, FR-004, FR-006
- **Implementation Details**: See [quickstart.md](quickstart.md)
- **Service Contracts**: See [contracts/](contracts/)
