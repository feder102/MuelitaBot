# Data Model: Cancel Appointment

**Phase**: 1 — Design  
**Date**: 2026-04-12  
**Feature**: 004-cancel-appointment

---

## Schema Changes

### 1. Appointment — Add `google_event_id`

**Table**: `appointments`  
**Change**: Add nullable column `google_event_id VARCHAR(255)`

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `google_event_id` | VARCHAR(255) | YES | NULL | Google Calendar event ID; stored at booking; used for deletion at cancellation |

**Index**: `ix_appointments_google_event_id` (non-unique, for future lookups)

**Migration**: Alembic auto-generates; existing rows default to NULL. Cancellation of rows with NULL `google_event_id` skips calendar delete and logs a warning.

---

### 2. ConversationStateEnum — Add New States

**Table**: `conversation_states` (column: `current_state`)  
**Change**: Add two new enum values

| New Value | Meaning |
|-----------|---------|
| `SELECTING_CANCELLATION_APPOINTMENT` | Patient is viewing their upcoming appointments list and must send a number to select one |
| `AWAITING_CANCELLATION_CONFIRMATION` | Patient has selected an appointment; system is waiting for "si" / "no" confirmation |

**Migration**: Alembic `op.execute("ALTER TYPE conversationstateenum ADD VALUE ...")`

---

## Context Data Shapes

`ConversationState.context_data` (JSON) is used during multi-step flows to store transient state. New shapes for the cancellation flow:

### State: `SELECTING_CANCELLATION_APPOINTMENT`

```json
{
  "cancellable_appointments": [
    {
      "index": 1,
      "appointment_id": "<uuid>",
      "dentist_name": "Hector",
      "appointment_date": "2026-04-20",
      "start_time": "10:00",
      "end_time": "11:00"
    },
    {
      "index": 2,
      "appointment_id": "<uuid>",
      "dentist_name": "Fulano",
      "appointment_date": "2026-05-03",
      "start_time": "14:00",
      "end_time": "15:00"
    }
  ]
}
```

### State: `AWAITING_CANCELLATION_CONFIRMATION`

```json
{
  "selected_appointment_id": "<uuid>",
  "dentist_name": "Hector",
  "appointment_date": "2026-04-20",
  "start_time": "10:00",
  "google_event_id": "<google_event_id_or_null>"
}
```

---

## Query Patterns

### Fetch Patient's Upcoming Appointments (for cancellation list)

```
SELECT a.*
FROM appointments a
WHERE a.patient_user_id = :user_uuid
  AND a.status = 'PENDING'
  AND (
    a.appointment_date > CURRENT_DATE
    OR (a.appointment_date = CURRENT_DATE AND a.start_time > CURRENT_TIME)
  )
ORDER BY a.appointment_date ASC, a.start_time ASC
```

**Notes**:
- Filters on `patient_user_id` (FK to TelegramUser) — ensures patients only see their own appointments.
- Excludes past appointments and appointments happening right now.
- Orders chronologically so the patient sees the nearest appointment first.
- N+1 prevention: load `dentist` relationship eagerly (joinedload) to get `dentist.name` without a second query.

### Mark Appointment as Cancelled

```
UPDATE appointments
SET status = 'CANCELLED', updated_at = NOW()
WHERE id = :appointment_uuid
  AND patient_user_id = :user_uuid
  AND status = 'PENDING'
```

**Notes**:
- The double-check on `patient_user_id` in the UPDATE is a safety guard against timing attacks (e.g., context_data tampered in a concurrent session).
- The `status = 'PENDING'` guard prevents double-cancellation races.
- If `rowcount == 0`, the appointment was already cancelled or doesn't belong to this user → return an error message, do not proceed to calendar delete.

---

## Entities (unchanged, referenced for clarity)

| Entity | Relevant Fields for This Feature |
|--------|----------------------------------|
| `TelegramUser` | `id` (UUID), `telegram_user_id` (BigInteger) — patient identity |
| `Appointment` | `id`, `patient_user_id`, `dentist_id`, `appointment_date`, `start_time`, `status`, `google_event_id` (NEW) |
| `Dentist` | `id`, `name`, `calendar_id` — needed to call Google Calendar delete |
| `ConversationState` | `user_id`, `current_state`, `context_data` — drives the cancellation flow |
| `AuditLog` | `user_id`, `action`, `details`, `timestamp` — cancellation logged here |
