# Implementation Plan: Multi-Dentist Appointment Booking

**Branch**: `003-multi-dentist-booking` | **Date**: 2026-04-05 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-multi-dentist-booking/spec.md`

## Summary

This feature extends the existing single-calendar appointment booking system to support multiple dentists, each with their own Google Calendar. Users selecting "appointment" from the bot menu will be prompted to choose which dentist they want to book with, with that selection determining which calendar receives the appointment. The system maintains a configurable list of dentists and their calendar IDs, enabling easy addition or removal of practitioners without code changes. This implementation preserves backward compatibility with the existing appointment booking flow while adding multi-dentist support at the bot interaction layer and persisting the dentist context through the booking process.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: FastAPI, SQLAlchemy (async ORM), google-api-python-client, python-telegram-bot, Pydantic  
**Storage**: PostgreSQL (async via asyncpg)  
**Testing**: pytest, pytest-asyncio  
**Target Platform**: Linux server (backend service)  
**Project Type**: Web service (Telegram bot with FastAPI backend)  
**Performance Goals**: Sub-second appointment booking flows (same as existing)  
**Constraints**: Medical system (security-first, encrypted data, audit logging per Constitution)  
**Scale/Scope**: Currently 2 dentists (Hector, Fulano); designed to scale to N dentists without code changes

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Core Principles Evaluation**:

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Clean Code & Simplicity** | ✅ PASS | Feature adds a new entity (Dentist) but maintains single responsibility. Selection logic is straightforward. |
| **II. Security-First Design** | ✅ PASS | No new security vulnerabilities. Maintains existing PHI protection and Google Calendar auth patterns. |
| **III. Performance & Scalability** | ✅ PASS | Database queries optimized with proper indexing on dentist_id. Caching can be applied to dentist list. |
| **IV. Test-First & Reliability** | ✅ PASS | New models/services require unit tests (>80% coverage), integration tests for dentist selection flow. |
| **V. Extensibility & Data Integrity** | ✅ PASS | This feature is exactly what this principle enables—clean support for multiple doctors without code duplication. |

**Security & Compliance**:
- ✅ No new authentication changes required
- ✅ Audit logging continues for all appointment operations (dentist_id tracked)
- ✅ Google Calendar API credentials remain secure
- ✅ No hardcoded dentist configurations

**Architecture & Design**:
- ✅ Stateless backend preserved (dentist selection passed through conversation state)
- ✅ Database-as-source-of-truth maintained (dentist list and appointments persisted)
- ✅ Doctor/Calendar abstraction aligns with constitutional "Doctor/Calendar abstraction" principle

**STATUS: ✅ PASS - No violations. Feature aligns perfectly with constitution.**

## Project Structure

### Documentation (this feature)

```text
specs/003-multi-dentist-booking/
├── plan.md                      # This file
├── research.md                  # Phase 0 output (not yet created)
├── data-model.md                # Phase 1 output (not yet created)
├── quickstart.md                # Phase 1 output (not yet created)
├── contracts/                   # Phase 1 output (not yet created)
│   └── dentist-selection.md     # Dentist selection flow contract
└── checklists/
    └── requirements.md          # Quality checklist
```

### Source Code Structure

```text
src/
├── models/
│   ├── appointment.py           # Extend: add dentist_id FK
│   ├── dentist.py               # NEW: Dentist entity
│   └── ...
├── services/
│   ├── appointment_service.py   # Extend: pass dentist_id through flow
│   ├── dentist_service.py       # NEW: Dentist CRUD & retrieval
│   ├── appointment_router.py    # Extend: handle dentist selection
│   ├── menu_router.py           # Extend: add dentist selection logic
│   └── ...
├── schemas/
│   ├── appointment.py           # Extend: add dentist field to schemas
│   └── dentist.py               # NEW: Dentist request/response schemas
├── api/
│   └── webhook.py               # Extend: Telegram message parsing for dentist selection
└── ...

tests/
├── unit/
│   ├── test_dentist_service.py          # NEW
│   ├── test_appointment_service.py      # Extend: multi-dentist scenarios
│   └── test_appointment_router.py       # Extend: dentist selection logic
├── integration/
│   └── test_multi_dentist_booking_flow.py  # NEW: E2E dentist selection + booking
└── ...

migrations/
└── [alembic auto-generated]     # NEW: Migration to add dentist table & appointment.dentist_id FK
```

**Structure Decision**: Single project structure maintained (existing pattern). Feature extends existing `src/models/`, `src/services/`, `src/schemas/` with new Dentist entity and related services. Tests added to existing test structure with new integration test for full flow.

## Complexity Tracking

No Constitution violations. Feature is a straightforward extension of existing appointment system with:
- 1 new entity (Dentist)
- 2 new services (DentistService for CRUD, extend AppointmentService for dentist context)
- 1 DB migration (add dentist table, FK in appointments)
- Conversation state extended to track selected dentist
- All changes additive, no breaking changes to existing code
