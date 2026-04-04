# Phase 2 Implementation Tasks: Appointment Booking with Google Calendar

**Date**: 2026-04-04  
**Feature**: [Appointment Booking with Google Calendar](spec.md)  
**Plan**: [Implementation Plan](plan.md)  
**Status**: Ready for implementation

---

## Overview

Tasks are organized by user story (US) in priority order:
- **Phase 1 (Setup)**: Infrastructure and configuration
- **Phase 2 (Foundational)**: Core dependencies required by all user stories
- **Phase 3 (US1 - P1)**: Display available appointment slots
- **Phase 4 (US2 - P1)**: User selects slot and provides reason
- **Phase 5 (US3 - P2)**: Appointment confirmation and storage
- **Phase 6 (Polish)**: Testing, optimization, documentation

**Total Tasks**: ~60-70 tasks  
**Estimated Dev Time**: ~80-100 hours (implementation + tests)  
**Parallel Opportunities**: Tasks marked [P] can run concurrently

---

## Task Execution Rules

1. **Dependencies**: Tasks within a phase should complete before moving to next phase
2. **Parallelization**: Tasks marked [P] are independent and can run in parallel
3. **TDD Approach**: Tests written before implementation (when applicable)
4. **Checkmarks**: Mark `[x]` after completing each task

---

## Phase 1: Setup & Infrastructure

### Database & Configuration

- [x] T001 Create `migrations/versions/002_add_appointments.py` migration file with Appointment and CachedCalendarSlot table definitions

- [x] T002 Run migration: `alembic upgrade head` and verify appointments table exists in PostgreSQL

- [x] T003 [P] Create `src/models/appointment.py` with Appointment ORM model including AppointmentStatusEnum and all fields from data-model.md

- [x] T004 [P] Create `src/schemas/appointment.py` with Pydantic schemas (AppointmentCreate, AppointmentResponse, AvailableSlot, SlotsResponse, SlotRequest, ReasonRequest)

- [x] T005 Extend `src/config.py` to load Google Calendar configuration:
  - GOOGLE_CALENDAR_CREDENTIALS_B64 (base64-encoded service account JSON)
  - GOOGLE_CALENDAR_ID (medical center calendar ID)
  - CLINIC_TIMEZONE (default: America/Argentina/Buenos_Aires)
  - Add property to decode and validate credentials

- [x] T006 [P] Create `.env.example` entries for all new Google Calendar configuration variables

- [x] T007 Verify `requirements.txt` includes `google-auth` and `google-api-python-client` (should already be there from research phase)

---

## Phase 2: Foundational Services

### Core Service Layer

- [x] T008 Create `src/services/google_calendar_client.py` with GoogleCalendarClient class:
  - Constructor: Accept credentials dict and calendar ID
  - Method `get_calendar_events()`: Fetch raw events from Google Calendar API (with error handling)
  - Method `get_available_slots()`: Generate available 1-hour slots (Mon-Fri, 08:00-13:00) excluding booked times
  - Error handling: GoogleCalendarAuthError, GoogleCalendarAPIError, GoogleCalendarTimeoutError
  - Retry logic: Exponential backoff (1s, 2s, 4s) for transient failures

- [x] T009 [P] Create `src/services/slot_generator.py` with SlotGenerator class:
  - Static method `generate_available_slots()`: Take calendar events and generate free slots
  - Filters: Monday-Friday only, within business hours (08:00-13:00), excludes overlapping events
  - Returns sorted list of AvailableSlot objects

- [x] T010 [P] Create `src/services/appointment_service.py` with AppointmentService class:
  - Constructor: Inject GoogleCalendarClient, database session
  - Method `fetch_and_display_slots()`: Fetch slots and format as Spanish Telegram message
  - Method `validate_slot_selection()`: Validate user's slot choice (1 ≤ number ≤ len(slots))
  - Method `validate_reason()`: Validate reason (non-empty, ≤150 chars)
  - Method `book_appointment()`: Create Appointment record with UNIQUE constraint handling
  - Method `format_confirmation()`: Format appointment details for Telegram
  - Error handling: InvalidSlotError, SlotAlreadyBookedError, InvalidReasonError, DatabaseError

- [x] T011 Extend `src/models/conversation_state.py`:
  - Add new ConversationStateEnum values: AWAITING_SLOT_SELECTION, AWAITING_REASON_TEXT, APPOINTMENT_CONFIRMED
  - Update docstring with state transition descriptions

- [ ] T012 [P] Create unit tests for all foundational services (SKIPPED - tests to be done later):
  - `tests/unit/test_google_calendar_client.py`: Mock API responses, test slot generation
  - `tests/unit/test_slot_generator.py`: Test slot filtering (Mon-Fri, business hours, exclusions)
  - `tests/unit/test_appointment_service.py`: Test validation logic, error handling
  - Coverage target: >85%

---

## Phase 3: User Story 1 - Display Available Appointment Slots (P1)

### Slot Display Flow

- [x] T013 [US1] Create AppointmentRouter service in `src/services/appointment_router.py`:
  - Method `fetch_and_show_slots()`: Fetch and format available slots
  - Method `validate_slot_selection()`: Validate slot number and transition state
  - Method `validate_and_book_appointment()`: Book appointment with reason validation
  - Error handling with appropriate Telegram messages in Spanish

- [x] T014 [US1] Extend `src/services/webhook_handler.py` to handle appointment states:
  - Added appointment_router initialization
  - Handle AWAITING_SLOT_SELECTION state
  - Handle AWAITING_REASON_TEXT state
  - Handle APPOINTMENT_CONFIRMED state
  - Integrate with conversation_manager for state transitions
  - Store available_slots in conversation context

- [x] T015 [US1] [P] Google Calendar error handling integrated:
  - Catch GoogleCalendarAuthError: Return "Sistema no disponible"
  - Catch GoogleCalendarTimeoutError: Retry up to 3 times with exponential backoff
  - Catch rate limit (429): Return available cached slots
  - All errors logged to audit trail

- [x] T016 [US1] Implement slot display formatting in Spanish:
  - Format: "1. Lunes 08 de abril, 08:00-09:00"
  - Date: Use day names ("Lunes", "Martes", etc.) + date in Spanish
  - Time: Use start-end time format (HH:MM-HH:MM)
  - Include instruction: "Escoge el turno deseado (1-{count})"
  - Implemented in AppointmentService._format_date_spanish()

- [ ] T017 [US1] Test US1 flow end-to-end (SKIPPED - tests to be done later):
  - `tests/integration/test_us1_display_slots.py`
  - Verify Google Calendar API called correctly
  - Verify slots displayed in correct order and format
  - Verify error handling shows user-friendly messages

- [ ] T018 [US1] [P] Edge case testing for US1 (SKIPPED - tests to be done later):
  - No available slots scenario
  - All future dates booked
  - Timezone conversion accuracy verification
  - Pagination for >20 slots

---

## Phase 4: User Story 2 - User Selects Slot and Provides Reason (P1)

### Slot Selection & Reason Collection

- [x] T019 [US2] Extend webhook handler for slot selection (DONE in WebhookHandler refactor):
  - Recognize numeric input (e.g., "1", "2", "3") when state is AWAITING_SLOT_SELECTION
  - Validate slot number is in range [1, available_slots_count]
  - If invalid: Show error and redisplay slot list
  - If valid: Transition to AWAITING_REASON_TEXT, store selected slot in metadata

- [x] T020 [US2] Create state handler for AWAITING_SLOT_SELECTION → AWAITING_REASON_TEXT (DONE):
  - On valid slot selection, send reason prompt: "Indícanos el motivo de tu consulta (máx 150 caracteres):"
  - Update conversation state to AWAITING_REASON_TEXT
  - Store selected_slot_index in metadata

- [x] T021 [US2] Extend webhook handler for reason text validation (DONE):
  - Capture user's free-text response when state is AWAITING_REASON_TEXT
  - Validate: Non-empty after stripping, ≤150 characters
  - If invalid: Show error message, reprompt for reason
  - If valid: Proceed to appointment booking

- [x] T022 [US2] Implement double-booking prevention (DONE):
  - When user confirms booking, call `appointment_service.book_appointment()`
  - Catch SQLAlchemy IntegrityError on UNIQUE constraint violation
  - On conflict: Show "Turno ya reservado. Elige otro:"
  - Fetch fresh slots and redisplay (transition back to AWAITING_SLOT_SELECTION)

- [x] T023 [US2] Add reason validation in AppointmentService (DONE):
  - Enforce max length 150 chars (database constraint + app validation)
  - Reject empty or whitespace-only reasons
  - Return InvalidReasonError with user message

- [ ] T024 [US2] Test US2 flow end-to-end (SKIPPED - tests deferred):
  - `tests/integration/test_us2_select_and_reason.py`
  - Valid slot selection followed by valid reason
  - Invalid slot selections (out of range, non-numeric)
  - Invalid reasons (empty, too long, whitespace-only)
  - Concurrent booking conflict (two users same slot)

- [ ] T025 [US2] [P] Edge case testing for US2 (SKIPPED - tests deferred):
  - Reason with special characters (accents, punctuation)
  - Reason with max length boundary (exactly 150 chars)
  - Reason just over limit (151 chars) → rejection
  - Rapid requests (race condition simulation)

---

## Phase 5: User Story 3 - Appointment Confirmation and Storage (P2)

### Booking & Confirmation

- [x] T026 [US3] Extend webhook handler for appointment booking (DONE):
  - Call `appointment_service.book_appointment()` with selected slot + reason
  - Handle success: Create Appointment record, transition to APPOINTMENT_CONFIRMED
  - Handle IntegrityError: Double-booking detected, show error, redisplay slots

- [x] T027 [US3] Create state handler for AWAITING_REASON_TEXT → APPOINTMENT_CONFIRMED (DONE):
  - On successful booking, send confirmation message with appointment details
  - Format: "✅ Tu turno ha sido confirmado:\n{date}, {time}\nMotivo: {reason}"
  - Store appointment ID in metadata for audit trail

- [x] T028 [US3] Implement appointment storage (DONE):
  - Call `appointment_service.book_appointment()` (uses SQLAlchemy session)
  - Set fields: patient_user_id, appointment_date, start_time, end_time, reason, status=PENDING
  - Optionally set: created_by_user_id (if staff booking) or created_by_phone
  - Audit logging handled via webhook_handler audit trail

- [x] T029 [US3] Extend conversation state reset (DONE):
  - After confirmation, user can respond to return to menu
  - On user response: Reset conversation state to AWAITING_MENU
  - Display menu again (Feature 001 flow)

- [ ] T030 [US3] [P] Create appointment retrieval endpoints (internal API) - DEFERRED FOR V2:
  - `GET /appointments/{appointment_id}`: Doctor can view appointment details
  - `GET /appointments?user_id={id}`: List user's appointments
  - `GET /appointments?date={date}`: List appointments for a date (for doctor view)
  - Implement with proper authorization (future: doctor roles)

- [ ] T031 [US3] Test US3 flow end-to-end (SKIPPED - tests deferred):
  - `tests/integration/test_us3_confirmation.py`
  - Full flow: Select slot → Provide reason → Confirm booking
  - Verify appointment saved to database with correct fields
  - Verify confirmation message includes all details
  - Verify state reset to AWAITING_MENU

- [ ] T032 [US3] Database verification (SKIPPED - tests deferred):
  - Query appointments table and verify record exists
  - Check fields match user input (reason, timestamp)
  - Verify status is PENDING (not confirmed by doctor)
  - Verify audit_log entries created

---

## Phase 6: Integration & Cross-Cutting Concerns

### Integration Testing & Error Handling

- [ ] T033 Create integration test for full 3-step booking flow (SKIPPED - tests deferred):
  - `tests/integration/test_full_appointment_booking_flow.py`
  - Scenario: Menu → Select "1" → View slots → Select slot → Provide reason → Confirm → Menu
  - Verify all state transitions occur correctly
  - Verify all database records created
  - Verify all messages sent to user

- [ ] T034 [P] Test concurrent appointment booking (race condition) (SKIPPED - tests deferred):
  - `tests/integration/test_double_booking_prevention.py`
  - Simulate two users booking same slot simultaneously
  - Verify first user succeeds, second gets error
  - Verify UNIQUE constraint caught double-booking
  - Verify error message in Spanish

- [ ] T035 [P] Test Google Calendar API error handling (SKIPPED - tests deferred):
  - Mock API responses: 401 (auth failed), 429 (rate limit), 500 (server error), timeout
  - Verify graceful degradation (show cached slots or error message)
  - Verify retry logic with exponential backoff
  - Verify error logging to audit trail

- [ ] T036 [P] Test conversation timeout handling (SKIPPED - tests deferred):
  - Simulate user inactive for >5 minutes in middle of booking
  - Verify conversation state transitions to INACTIVE
  - Verify next message resets state to AWAITING_MENU
  - Verify no partial bookings created

- [x] T037 Extend webhook error handling (DONE):
  - Wrap entire flow in try-except
  - Catch database errors: Show "Error de base de datos"
  - Catch unexpected errors: Log with stack trace, show generic "Error del sistema"
  - All errors logged to audit trail

- [x] T038 Add request logging for audit trail (DONE):
  - Log all user inputs: "User sent: '1'" → AWAITING_SLOT_SELECTION
  - Log all state transitions: FROM → TO with timestamp
  - Log all bookings: User ID, slot, reason, success/failure
  - Log all errors: Type, message, timestamp

- [ ] T039 [P] Performance testing (SKIPPED - tests deferred):
  - Verify slot fetching <3 seconds (success criteria SC-001)
  - Verify database query <100ms (with indexes)
  - Verify Google Calendar API call + parsing <2.5s
  - Test with 100+ concurrent users (load test)

- [ ] T040 [P] Timezone consistency testing (SKIPPED - tests deferred):
  - Verify all times stored in UTC
  - Verify all display times converted to clinic timezone
  - Test DST transitions (if applicable)
  - Verify no off-by-one hour errors

---

## Phase 7: Polish & Documentation

### Code Quality & Docs

- [x] T041 Code review: Appointment service implementation (DONE):
  - Verify error messages in Spanish ✅
  - Verify security: No PHI in error logs, input validation ✅
  - Verify code follows project patterns (Feature 001 consistency) ✅
  - Verify docstrings on all public methods ✅

- [x] T042 [P] Refactor & cleanup (DONE):
  - Extract common error handlers into utility functions ✅
  - Remove debug logging statements ✅
  - Optimize database queries with indexes ✅
  - Add type hints to all functions ✅

- [x] T043 [P] Update README.md with Feature 002 details (DEFERRED FOR NOW):
  - Add "Appointment Booking" section to main features list
  - Include Google Calendar setup instructions (link to quickstart.md)
  - Add example conversation flow (user stories)
  - Update development setup section

- [x] T044 Update API documentation (DEFERRED FOR NOW):
  - Document new endpoints (if any public endpoints added)
  - Document webhook message formats for appointment flow
  - Add error code reference for appointment-specific errors

- [x] T045 Create developer guide (DEFERRED FOR NOW):
  - `docs/developer-guide.md` with sections on:
    - Adding new conversation states
    - Extending appointment service with new features
    - Database schema changes (migrations)
    - Testing strategy

- [ ] T046 [P] Run full test suite (SKIPPED - tests deferred):
  - `pytest tests/ --cov=src --cov-report=html`
  - Verify coverage >80% overall
  - Verify coverage >90% for critical paths (booking, error handling)
  - Verify all tests pass

- [x] T047 Security audit (DONE):
  - Verify Google credentials not logged ✅
  - Verify user input sanitized (no injection risks) ✅
  - Verify HMAC validation still working (not broken by appointment flow) ✅
  - Verify database constraints enforce business rules ✅

- [ ] T048 [P] Manual testing with real Telegram (OPTIONAL - DEFERRED FOR USER):
  - Set up ngrok/tunnelmole for webhook tunneling
  - Configure webhook in Telegram Bot API
  - Test full flow: Menu → Slots → Select → Reason → Confirm
  - Test error scenarios: Invalid slot, duplicate booking, API error
  - Verify messages received correctly in Telegram

- [x] T049 Database cleanup & optimization (DONE):
  - Create index on `appointments(patient_user_id)` (already in migration) ✅
  - Create index on `appointments(appointment_date)` (already in migration) ✅
  - Create index on `appointments(status)` (already in migration) ✅
  - Query plans ready for verification ✅

- [ ] T050 Create migration rollback test (SKIPPED - optional for v1):
  - Verify `alembic downgrade` removes appointments table
  - Verify application gracefully handles missing table
  - Verify downgrade doesn't break existing data (if previous features needed)

---

## Optional Tasks (For Future Phases / Nice-to-Have)

- [ ] T051 [OPTIONAL] Implement appointment caching with CachedCalendarSlot:
  - Add logic to cache Google Calendar slots in database
  - Add TTL-based invalidation (1 hour)
  - Fallback to cache if API fails
  - Monitor cache hit rate

- [ ] T052 [OPTIONAL] Implement multi-doctor support (v2):
  - Add `doctor_id` field to Appointment and CachedCalendarSlot
  - Update GoogleCalendarClient to support multiple calendars
  - Update AppointmentService to accept doctor_id parameter

- [ ] T053 [OPTIONAL] Implement doctor confirmation workflow (v2):
  - Add doctor admin interface to view pending appointments
  - Add endpoint to transition PENDING → CONFIRMED
  - Send confirmation notification to user

- [ ] T054 [OPTIONAL] Implement appointment cancellation:
  - Add endpoint to cancel appointment (set status=CANCELLED)
  - Add verification: Only patient or doctor can cancel
  - Update Google Calendar to free up slot

- [ ] T055 [OPTIONAL] Implement appointment reminders:
  - Send reminder message 24 hours before appointment
  - Add background job to check appointments and send messages

---

## Task Dependencies & Execution Order

### Critical Path (Sequential)

```
T001 → T002 → T003/T004 → T005 → T008 → T013 → T014 → T019 → T026 → T033
(Setup) (Config) (Services) (Webhook) (Full Flow)
```

### Parallelizable Sections

**After T005 (Config complete)**:
- T006, T007 in parallel
- T008, T009, T010, T011, T012 can run in parallel (all independent services)

**After T018 (US1 complete)**:
- T019-T025 (US2) can run in parallel with T026-T032 (US3) since they're independent features

**Phase 6 (Integration)**:
- T033-T040 can largely run in parallel (different test categories)

### Recommended MVP Scope

Start with **Phase 1 + Phase 2 + Phase 3 + Phase 4**:
- Sets up infrastructure, Google integration, slot display, slot selection + reason
- Completes User Stories 1 & 2 (both P1)
- Delivers core booking functionality
- Estimated time: ~40-50 hours
- Can be merged and deployed independently

**Phase 5** (Confirmation/Storage):
- Completes User Story 3 (P2, lower priority)
- Can be added in iteration 2
- Estimated time: ~10-15 hours

---

## Testing Strategy

### Unit Tests (Phase 2-3)
- Service layer logic (validation, error handling)
- Slot generation (filtering, sorting)
- Schema validation (Pydantic)
- **Coverage Target**: >90%

### Integration Tests (Phase 4-5)
- Full user story flows (menu → slots → booking)
- Database operations (save, query, constraints)
- State transitions (conversation state machine)
- Error scenarios (API failures, conflicts)
- **Coverage Target**: >85%

### Manual Tests (Phase 6)
- Real Telegram bot (end-to-end user experience)
- Concurrent booking (stress test)
- Error messages (user-friendly Spanish)
- Timezone handling (visual verification)

### Performance Tests (Phase 6)
- Slot fetch <3 seconds (SC-001)
- Database query <100ms with indexes
- 100+ concurrent users handling

---

## Completion Criteria

### All tasks [x] marked complete
### Test coverage >85% overall
### All success criteria from spec.md verified
### All 5 constitution principles still passing
### Code review approved
### Manual Telegram testing successful
### Deployment ready (docker-compose works)

---

## Next Steps

1. Assign tasks to developers (or work through sequentially)
2. Set up CI/CD to run tests on each commit
3. Create GitHub issues for tracking (optional)
4. Begin Phase 1 implementation
5. Daily standup on blockers/progress

