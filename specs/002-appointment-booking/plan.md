# Implementation Plan: Appointment Booking with Google Calendar

**Branch**: `002-appointment-booking` | **Date**: 2026-04-04 | **Spec**: [Appointment Booking with Google Calendar](/specs/002-appointment-booking/spec.md)
**Input**: Feature specification from `/specs/002-appointment-booking/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Extend feature 001 webhook menu backend with Google Calendar integration for appointment booking. When user selects "Solicitar turno" (option 1), system fetches available slots (Mon-Fri, 08:00-13:00, 1-hour increments), displays them, allows user selection, prompts for consultation reason (max 150 chars), and stores appointment with staff tracking (user_id or phone). Prevents double-booking via concurrent-safe operations and provides confirmation to user.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: FastAPI, SQLAlchemy (async ORM), google-auth, google-api-python-client, python-telegram-bot  
**Storage**: PostgreSQL (extends existing schema with Appointment table)  
**Testing**: pytest + pytest-asyncio  
**Target Platform**: Linux server (Docker containerized)  
**Project Type**: Web-service (REST API backend with Telegram integration)  
**Performance Goals**: <3 seconds to fetch and display calendar slots, handle 100+ concurrent appointment requests  
**Constraints**: Google Calendar API rate limits, timezone consistency (UTC storage), prevent race conditions on slot booking  
**Scale/Scope**: Single doctor/calendar (v1), extensible to multiple calendars in v2+

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Clean Code & Simplicity
- **Gate**: Appointment booking flow separate from menu routing (single responsibility)
- **Gate**: Google Calendar integration encapsulated in dedicated service
- **Gate**: No complex state machines; simple state progression (PENDING → CONFIRMED)
- **Status**: ✅ PASS - Feature scope is focused and modular

### Principle II: Security-First Design
- **Gate**: Google Calendar credentials from environment variables (no hardcoded secrets)
- **Gate**: Appointment reason validated for length and content (150 char max)
- **Gate**: Staff tracking fields (created_by_user_id, created_by_phone) for audit
- **Gate**: Input validation on all user-provided data (slot selection, reason text)
- **Gate**: No PHI leakage in error messages (generic user messages, detailed server logs)
- **Status**: ✅ PASS - All security gates address constitution requirements

### Principle III: Performance & Scalability
- **Gate**: <3 second response time for slot fetching
- **Gate**: Concurrent appointment requests handled without race conditions
- **Gate**: Database queries optimized (no N+1 queries on appointment list)
- **Gate**: Google Calendar API results cached appropriately
- **Status**: ✅ PASS - Performance targets defined and achievable

### Principle IV: Test-First & Reliability
- **Gate**: >80% code coverage required (unit + integration tests)
- **Gate**: Integration tests with real PostgreSQL and mock Google Calendar
- **Gate**: Double-booking prevention tested with concurrent requests
- **Gate**: All tests must pass before merge
- **Status**: ✅ PASS - Testing strategy will be defined in Phase 1

### Principle V: Extensibility & Data Integrity
- **Gate**: Appointment schema supports future fields (doctor_id for multi-doctor v2)
- **Gate**: Calendar slot generation logic separate from storage (can swap calendar providers)
- **Gate**: Database constraints enforce data integrity (FK, NOT NULL, UNIQUE)
- **Status**: ✅ PASS - Data model designed for extensibility

## Project Structure

### Documentation (this feature)

```text
specs/002-appointment-booking/
├── spec.md                           # Feature specification ✅
├── plan.md                           # This file (implementation plan)
├── research.md                       # Phase 0 (technology decisions)
├── data-model.md                     # Phase 1 (entities and schema)
├── quickstart.md                     # Phase 1 (local setup guide)
├── contracts/                        # Phase 1 (API/service contracts)
│   └── appointment_booking.md
├── checklists/
│   └── requirements.md               # Specification validation ✅
└── tasks.md                          # Phase 2 (implementation tasks)
```

### Source Code (repository root)

```text
src/
├── models/
│   ├── appointment.py                # NEW: Appointment ORM model
│   └── [existing: telegram_user.py, conversation_state.py, audit_log.py]
├── services/
│   ├── google_calendar_client.py     # NEW: Google Calendar API wrapper
│   ├── appointment_service.py        # NEW: Appointment business logic
│   ├── slot_generator.py             # NEW: Generate available slots
│   └── [existing: message_parser.py, conversation_manager.py, menu_router.py, webhook_handler.py]
├── api/
│   └── webhook.py                    # EXTEND: Add appointment booking flow
├── schemas/
│   ├── appointment.py                # NEW: Pydantic schemas for appointments
│   └── [existing: telegram_webhook.py]
├── utils/
│   └── [existing: signature_validator.py, telegram_client.py, logger.py]
├── config.py                         # EXTEND: Add Google Calendar config
├── db.py                             # Existing database setup
└── main.py                           # Existing FastAPI app

migrations/
└── versions/
    ├── 001_initial_schema.py         # Existing
    └── 002_add_appointments.py       # NEW: Create Appointment table

tests/
├── unit/
│   ├── test_google_calendar_client.py   # NEW
│   ├── test_appointment_service.py      # NEW
│   └── test_slot_generator.py           # NEW
├── integration/
│   ├── test_appointment_booking_flow.py # NEW
│   └── test_double_booking_prevention.py # NEW
└── contract/
    └── test_appointment_booking.py      # NEW
```

**Structure Decision**: Single FastAPI application extended with appointment module. Adds 4 new service files, 2 new model/schema files, 2 new test modules. Follows existing pattern from feature 001: models → schemas → services → API. Google Calendar client isolated in dedicated service for clean separation of concerns.

## Complexity Tracking

No constitution violations. Feature integrates cleanly with existing architecture without requiring exceptions or special justification.
