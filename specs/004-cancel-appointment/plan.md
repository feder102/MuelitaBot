# Implementation Plan: Cancel Appointment

**Branch**: `004-cancel-appointment` | **Date**: 2026-04-12 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/004-cancel-appointment/spec.md`

## Summary

Add a "Cancelar turno" option to the Telegram bot main menu. When selected, the bot identifies the patient by their Telegram user ID, retrieves their upcoming PENDING appointments from the database, presents a numbered selection list, asks for confirmation, then marks the appointment as CANCELLED and deletes the corresponding Google Calendar event.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: FastAPI (async), SQLAlchemy (async ORM), python-telegram-bot (webhook mode), google-api-python-client, Alembic  
**Storage**: PostgreSQL (async via asyncpg)  
**Testing**: pytest + pytest-asyncio; integration tests against a real PostgreSQL test database (no mocks per constitution)  
**Target Platform**: Linux server  
**Project Type**: Web service (Telegram webhook backend)  
**Performance Goals**: Sub-second response for appointment list retrieval; all DB queries use indexed fields  
**Constraints**: No N+1 queries; all datetimes in UTC; error messages must not leak system internals  
**Scale/Scope**: Small clinic, low concurrent users; no pagination needed for appointment lists

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| Clean Code & Simplicity | ✅ PASS | `CancellationRouter` follows existing `AppointmentRouter` pattern; single responsibility |
| Security-First | ✅ PASS | Patient identity validated via Telegram user ID on every DB query; ownership double-checked in UPDATE WHERE; audit log written |
| Performance & Scalability | ✅ PASS | `joinedload` prevents N+1; queries on indexed `patient_user_id` and `status` |
| Test-First & Reliability | ✅ PASS | Unit + integration tests required; integration tests run against real DB |
| Extensibility & Data Integrity | ✅ PASS | Schema change is additive (nullable column); existing enum extended; no breaking changes |

No constitution violations — no Complexity Tracking entry required.

## Project Structure

### Documentation (this feature)

```text
specs/004-cancel-appointment/
├── plan.md                        # This file
├── research.md                    # Phase 0 — all decisions documented
├── data-model.md                  # Phase 1 — schema changes + query patterns
├── quickstart.md                  # Phase 1 — developer guide
├── contracts/
│   └── conversation-flow.md       # Phase 1 — state machine + message contracts
└── tasks.md                       # Phase 2 output (/speckit.tasks — not yet created)
```

### Source Code

```text
backend/src/
├── models/
│   ├── appointment.py             # MODIFY: add google_event_id column
│   └── conversation_state.py     # MODIFY: add 2 new enum values
├── services/
│   ├── cancellation_router.py    # CREATE: new state-machine handler
│   ├── google_calendar_client.py # MODIFY: add delete_event()
│   ├── appointment_service.py    # MODIFY: save google_event_id after create
│   ├── webhook_handler.py        # MODIFY: wire new states + option "3"
│   ├── menu_router.py            # MODIFY: add option 3 to menu text/routing
│   └── message_parser.py         # MODIFY: recognize "3", "cancelar", "si", "no"

migrations/versions/
└── <hash>_add_google_event_id_and_cancel_states.py   # CREATE: Alembic migration

tests/
├── unit/
│   └── test_cancellation_router.py       # CREATE
└── integration/
    └── test_cancel_appointment_flow.py   # CREATE
```

**Structure Decision**: Single-project layout (existing `src/` tree). No new top-level directories needed; the cancellation feature slots into the existing service layer.
