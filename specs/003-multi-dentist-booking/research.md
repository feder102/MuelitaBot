# Research & Technical Decisions: Multi-Dentist Appointment Booking

**Date**: 2026-04-05 | **Feature**: 003-multi-dentist-booking

## Overview

This document consolidates research findings and technical decisions required for implementing multi-dentist support in the appointment booking system. All NEEDS CLARIFICATION items from the specification have been researched and resolved.

---

## Research Findings

### 1. Dentist Configuration Storage & Retrieval

**Decision**: Store dentists in a dedicated `dentist` database table rather than environment variables or hardcoded lists.

**Rationale**:
- Enables runtime configuration (add/remove dentists without deployment)
- Supports future features like dentist availability, schedules, or patient-dentist associations
- Aligns with Constitution Principle V (Extensibility & Data Integrity): "Configuration separate from code"
- Allows audit logging of dentist roster changes

**Alternatives Considered**:
1. Environment variables (`.env`): Rejected because changes require redeployment
2. JSON file in repository: Rejected for same reason; not audit-tracked
3. External config service: Premature over-engineering; database table sufficient for MVP

**Implementation**: Create `Dentist` ORM model with fields: `id`, `name`, `calendar_id`, `active_status`, `created_at`, `updated_at`

---

### 2. Dentist Selection in Telegram Bot

**Decision**: Implement dentist selection as a separate menu step after user selects "appointment" option.

**Rationale**:
- Matches existing conversation flow pattern (menu → selection → action)
- Telegram bot interaction model is naturally sequential
- Maintains conversation state via existing `ConversationState` model
- Avoids overwhelming user with too many options at once

**Alternatives Considered**:
1. Inline keyboard with all dentist buttons: Viable, but harder to extend beyond 10 dentists; less UX-scalable
2. Voice/button-based selection (1 for Hector, 2 for Fulano): Selected for MVP

**Implementation**: Add `selected_dentist_id` field to `ConversationState` model; handle dentist selection in `appointment_router.py` before displaying slots

---

### 3. Google Calendar API Multi-Calendar Support

**Decision**: Reuse existing `GoogleCalendarClient` by passing `calendar_id` as a parameter rather than hardcoding it.

**Rationale**:
- Existing API client already supports multiple calendar IDs (no implementation changes needed to Google integration)
- Tested pattern from Feature 002 already validates calendar access
- Minimizes risk and complexity

**Alternatives Considered**:
1. Create separate `GoogleCalendarClient` per dentist: Unnecessary complexity; wasted connections
2. Cache all dentist calendars at startup: Premature optimization; single-call-per-booking is acceptable

**Implementation**: `AppointmentService.get_available_slots()` now takes `dentist_id` parameter; looks up dentist's `calendar_id` and passes to Google client

---

### 4. Appointment Uniqueness Constraints

**Decision**: Unique constraint on `(dentist_id, appointment_date, start_time)` instead of just `(appointment_date, start_time)`.

**Rationale**:
- Multiple dentists can have the same time slot booked independently
- Prevents double-booking within a single dentist's calendar
- Aligns with real-world dental practice (each doctor has own schedule)

**Alternatives Considered**:
1. Keep global uniqueness: Would prevent multi-dentist support; rejected
2. Remove uniqueness constraint: Introduces double-booking bugs; too risky

**Implementation**: Update `Appointment` model constraint to include `dentist_id` in the unique index

---

### 5. Dentist Availability & Empty List Handling

**Decision**: When no dentists are available (empty list or all inactive), bot displays message and offers secretary contact option.

**Rationale**:
- Graceful degradation; prevents bot from appearing broken
- Matches existing error handling pattern (e.g., when no calendar slots available)
- Matches User Story edge case: "What happens when the dentist list is empty?"

**Alternatives Considered**:
1. Return error 500: Poor UX
2. Prompt user to contact admin: Requires external communication; out of scope

**Implementation**: Validate dentist list in `appointment_router.py`; display user-friendly message if empty

---

### 6. Backward Compatibility

**Decision**: Implement multi-dentist as **additive only** — no changes to existing single-dentist logic if only one active dentist exists.

**Rationale**:
- Preserves existing system behavior
- Reduces regression risk
- Meets Success Criteria SC-004: "System maintains backward compatibility"

**Alternatives Considered**:
1. Always show dentist selection: Changes behavior even for single-dentist clinics; unnecessary
2. Auto-select if only one dentist: Still changes flow; less explicit

**Implementation**: If exactly 1 active dentist, auto-select and skip the selection menu; otherwise show selection. Both paths store `dentist_id` consistently.

---

### 7. Error Handling: Dentist Calendar Unreachable

**Decision**: When a dentist's calendar cannot be reached (invalid `calendar_id` or permissions issue), catch `GoogleCalendarError` and display user-friendly message offering to retry or contact secretary.

**Rationale**:
- Matches existing error handling (Feature 002 already handles Google API failures)
- Prevents system crash; provides fallback
- Aligns with Constitution security principle: "Error messages must not leak system details to clients"

**Alternatives Considered**:
1. Retry automatically: May hide persistent issues
2. Silently skip dentist: Confusing UX; user thinks dentist is unavailable

**Implementation**: Extend `appointment_router.py` error handling; wrap Google calendar calls in try/except per existing pattern

---

### 8. Database Migration Strategy

**Decision**: Use Alembic (existing pattern) to:
1. Create `dentist` table
2. Add `dentist_id` column to `appointments` table (nullable initially for rollback safety)
3. Populate `dentist_id` for existing appointments (if any) with a default/placeholder dentist
4. Add foreign key constraint

**Rationale**:
- Alembic already in use for Schema 002 (Appointment table)
- Allows zero-downtime deployment
- Reversible if needed

**Alternatives Considered**:
1. Make `dentist_id` non-nullable from start: Requires data migration before adding constraint
2. Separate migrations: Over-complicates process

**Implementation**: Single Alembic migration with explicit migration steps

---

## Resolved NEEDS CLARIFICATION Items

**From original spec**: No [NEEDS CLARIFICATION] markers existed in spec. All unknowns resolved above through research and informed defaults.

---

## Technology Validation

All chosen technologies already in use or directly compatible:

| Technology | Current Use | Validation |
|-----------|-------------|-----------|
| Python 3.11+ | ✅ In use (Feature 002) | No version constraints added by multi-dentist feature |
| FastAPI | ✅ In use | No new framework changes required |
| SQLAlchemy | ✅ In use (async) | No new constraints; async pattern maintained |
| PostgreSQL | ✅ In use | No new requirements; standard SQL sufficient |
| google-api-python-client | ✅ In use (Feature 002) | Supports multiple calendar_ids natively |
| python-telegram-bot | ✅ In use (Feature 001) | No new limitations; conversation flow extended naturally |
| Pydantic | ✅ In use | Used for schema validation; new Dentist schemas follow existing pattern |

**Conclusion**: No new technology risks. Feature is purely architectural extension of existing system.

---

## Success Metrics - Technical Validation

| Metric | How Achieved |
|--------|--------------|
| SC-001: Booking within existing avg time | Dentist lookup is single DB query; no performance regression |
| SC-002: 100% accuracy in routing | Dentist_id stored with appointment; verified in unit tests |
| SC-003: New dentists visible within 5 min | DB insert is immediate; conversation state refreshes on next bot interaction |
| SC-004: Backward compatibility | Single-dentist clinics skip selection menu; flow identical |
| SC-005: 95% success rate | Error handling matches existing appointment booking reliability |
| SC-006: Intuitive menu | Follows existing Telegram bot UX patterns (numbered options) |

---

## Dependencies & Integration Points

**Database Dependencies**:
- `TelegramUser` table (existing): Appointment still FKs to patient
- `Appointment` table (existing): Extended with `dentist_id` FK
- `ConversationState` table (existing): Extended with `selected_dentist_id`

**API Dependencies**:
- Google Calendar API: No changes; multi-calendar support already built-in
- Telegram Bot API: No changes; conversation flow follows existing pattern

**Service Dependencies**:
- `GoogleCalendarClient`: No changes; accept dentist's `calendar_id` as parameter
- `AppointmentService`: Extended to accept `dentist_id` context
- `ConversationManager`: Extended to track selected dentist
- `AppointmentRouter`: Adds dentist selection step before slot display

---

## Deployment Considerations

1. **Database Migration**: Must run before deploying new code (safe even if new code not deployed yet)
2. **Zero-Downtime**: Dentist selection optional in early phase; old flow still works with missing `dentist_id`
3. **Rollback**: Migration is reversible; code changes are additive (no breaking changes)
4. **Monitoring**: Track API calls to Google Calendar per dentist to ensure no one dentist is overwhelmed

---

## Next Steps

All research complete. Ready for Phase 1: Design & Data Model generation.
