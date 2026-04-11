# Implementation Tasks: Multi-Dentist Appointment Booking

**Feature**: 003-multi-dentist-booking | **Date**: 2026-04-05 | **Branch**: 003-multi-dentist-booking

## Overview

This document contains all implementation tasks for extending the appointment booking system to support multiple dentists. Tasks are organized by user story (P1 → P3) with dependencies tracked. Each task is independently executable with a clear success criterion.

---

## Task Summary

- **Total Tasks**: 27
- **Setup Phase**: 2 tasks
- **Foundational Phase**: 5 tasks
- **User Story 1 (P1)**: 12 tasks
- **User Story 2 (P2)**: 4 tasks
- **User Story 3 (P3)**: 3 tasks
- **Polish Phase**: 1 task

**Estimated Complexity**: Medium (extends existing patterns, no new frameworks)

---

## Implementation Strategy

### MVP Scope (Recommended for Initial Release)

**Release 1**: User Stories P1 + P3
- Patients can select dentist and book appointments ✅
- Dentist configuration is manageable via database ✅
- Secretary feature deferred to Release 2

**Release 2**: User Story P2
- Secretary can manage appointments across all dentists

### Parallelizable Work

Within each user story phase, the following can be done in parallel:
- **[P]** Model definitions (no service dependencies)
- **[P]** Schema definitions (no service dependencies)
- **[P]** Service implementations (different services)
- **[P]** Tests for different components

---

## Phase 1: Setup & Infrastructure

### Database Migration

- [X] T001 Create Alembic migration file `migrations/versions/[timestamp]_add_dentist_table.py` with:
  - CREATE TABLE dentists (id, name, calendar_id, active_status, timestamps)
  - ADD COLUMN dentist_id to appointments (nullable initially)
  - CREATE indexes on dentist.active_status and appointment.dentist_id
  - ADD FOREIGN KEY constraint with ON DELETE RESTRICT
  - Follow existing migration pattern from Feature 002

### Project Structure

- [ ] T002 Verify existing project structure and confirm all directories exist:
  - `src/models/`, `src/services/`, `src/schemas/`, `src/api/`
  - `tests/unit/`, `tests/integration/`
  - Create `/tests/unit/test_dentist_service.py` stub (empty file for placeholder)

---

## Phase 2: Foundational Components (Blocking Prerequisites)

These components are shared by all user stories and must be completed first.

### Database & Models

- [X] T003 [P] Create Dentist ORM model in `src/models/dentist.py`:
  - Fields: id (UUID PK), name (unique string, 100 chars), calendar_id (unique string, 255 chars)
  - Fields: active_status (boolean, default True), created_at, updated_at (timestamps)
  - Indexes: idx_dentist_active_status, idx_dentist_name
  - Relationships: appointments (backref)
  - Validation: name 1-100 chars, calendar_id non-empty
  - See [data-model.md](data-model.md) Entity 1 for details

- [X] T004 [P] Extend Appointment model in `src/models/appointment.py`:
  - Add dentist_id column (UUID FK to dentists.id, nullable initially, indexed)
  - Update unique constraint from (appointment_date, start_time) to (dentist_id, appointment_date, start_time)
  - Add relationship: dentist = relationship("Dentist", back_populates="appointments")
  - Update __repr__ to include dentist_id
  - See [data-model.md](data-model.md) Entity 2 for details

### Schemas & Validation

- [X] T005 [P] Create Dentist Pydantic schemas in `src/schemas/dentist.py`:
  - DentistResponse: id, name, calendar_id, active_status (read model)
  - DentistCreate: name, calendar_id, active_status=True (write model)
  - Both use Config.from_attributes = True for ORM compatibility
  - Validation: name 1-100 chars, calendar_id non-empty string

- [X] T006 [P] Extend Appointment schemas in `src/schemas/appointment.py`:
  - Add dentist_id field to AppointmentCreate schema
  - Add dentist_id field to AppointmentResponse schema
  - Update AvailableSlot schema if needed to include dentist context

### Conversation State Extension

- [X] T007 Extend ConversationState handling in `src/services/conversation_manager.py`:
  - Ensure set_step() and get_step() properly handle step_context JSON
  - Support new step: SELECTING_DENTIST
  - Support new context field: selected_dentist_id (stored in step_context JSON)
  - No schema changes (JSON field already exists)
  - Verify compatibility with existing conversation flow

---

## Phase 3: User Story 1 - Appointment Booking with Dentist Selection (P1)

**Goal**: Patients can select a specific dentist and complete appointment booking with that dentist.

**Acceptance Criteria**:
1. User selects "1 - Appointment" from menu
2. If 2+ dentists active: bot displays dentist selection menu with numbers
3. User selects dentist number (e.g., "1" for Hector)
4. Bot shows available slots for that dentist
5. User selects slot and provides reason
6. Appointment created in selected dentist's calendar with dentist_id stored

**Independent Test**: Can be tested standalone by:
- Creating 2+ dentists in DB
- Simulating user selecting appointment → selecting dentist → selecting slot → confirming
- Verifying appointment record includes correct dentist_id
- Verifying appointment appears in correct Google Calendar

### DentistService Implementation

- [X] T008 Create DentistService in `src/services/dentist_service.py`:
  - Method: get_active_dentists(session) → List[Dentist]
    - SELECT * FROM dentists WHERE active_status = TRUE ORDER BY name
    - Returns list of active dentists for booking menu
  - Method: get_dentist_by_id(session, dentist_id) → Optional[Dentist]
    - SELECT * FROM dentists WHERE id = ? AND active_status = TRUE
    - Raises DentistNotFoundError if not found or inactive
  - Method: get_dentist_calendar_id(session, dentist_id) → str
    - Looks up dentist by ID, returns calendar_id
    - Raises DentistNotFoundError if not found
  - Error classes: DentistNotFoundError, DentistInactiveError
  - See [quickstart.md](quickstart.md) Section 4 for implementation details

### AppointmentService Extension

- [X] T009 Extend AppointmentService in `src/services/appointment_service.py`:
  - Update __init__ to accept dentist_service parameter
  - Update get_available_slots(session, dentist_id) signature:
    - Add dentist_id parameter
    - Call dentist_service.get_dentist_by_id() to validate and get calendar_id
    - Pass calendar_id to google_calendar_client
    - Return filtered slots for that dentist
  - Update book_appointment(session, patient_user_id, dentist_id, ...) signature:
    - Add dentist_id parameter (required)
    - Validate dentist exists and is active before booking
    - Check for conflicts using new unique constraint
    - Create Appointment record with dentist_id set
  - See [quickstart.md](quickstart.md) Section 5 for details

### AppointmentRouter Dentist Selection Logic

- [X] T010 Extend AppointmentRouter in `src/services/appointment_router.py`:
  - Add method: handle_appointment_selection(session, user_id, telegram_user) → str
    - Get active dentists: active_dentists = await dentist_service.get_active_dentists(session)
    - If 0 dentists: return error message "No dentists available. Contact secretary."
    - If 1 dentist: auto-select and set step to WAITING_FOR_APPOINTMENT with selected_dentist_id
    - If 2+ dentists: return menu text with numbered list, set step to SELECTING_DENTIST
    - Return appropriate message (Spanish)
    - See [contracts/dentist-selection.md](contracts/dentist-selection.md) Message 3a/3b for exact text
  - Add method: handle_dentist_selected(session, user_id, selection_number) → str
    - Parse selection_number (e.g., "1")
    - Look up dentist from state context
    - Validate selection is in range and dentist still active
    - Set state to WAITING_FOR_APPOINTMENT with selected_dentist_id
    - Return message transitioning to show slots
    - Handle invalid selection: repeat menu with error
  - Update show_available_slots() to accept dentist_id parameter
    - Call appointment_service.get_available_slots(session, dentist_id)
    - Format slots with dentist name in response (confirmation message)
  - See [quickstart.md](quickstart.md) Section 6 for implementation details

### MenuRouter Integration

- [ ] T011 Extend MenuRouter in `src/services/menu_router.py`:
  - When user sends "1" (appointment option):
    - Call: await self.appointment_router.handle_appointment_selection(session, user_id, telegram_user)
    - Return the result message
  - Ensure menu flow transitions to appointment_router correctly

### Conversation State Transitions

- [X] T012 [US1] Update appointment_router message flow handling in `src/api/webhook.py`:
  - After user selects appointment (sends "1"):
    - Check current_step and call appropriate handler
    - If step == SELECTING_DENTIST and user sends number:
      - Call handle_dentist_selected(session, user_id, selection_number)
      - Continue to appointment selection flow
    - Ensure state machine follows [contracts/dentist-selection.md](contracts/dentist-selection.md) state diagram
  - Test state transitions with all dentist count scenarios

### Tests for User Story 1

- [ ] T013 [P] [US1] Create unit tests in `tests/unit/test_dentist_service.py`:
  - Test get_active_dentists() returns only active dentists
  - Test get_active_dentists() returns empty list when none active
  - Test get_dentist_by_id() with valid ID returns dentist
  - Test get_dentist_by_id() with invalid ID raises DentistNotFoundError
  - Test get_dentist_by_id() ignores inactive dentist (raises error)
  - Test get_dentist_calendar_id() returns calendar_id for valid dentist
  - Fixtures: create_dentist_service, test_dentists (Hector, Fulano)
  - See [quickstart.md](quickstart.md) "Test Data Setup" for fixture pattern

- [ ] T014 [P] [US1] Create unit tests in `tests/unit/test_appointment_router.py`:
  - Test handle_appointment_selection() with 0 dentists returns error message
  - Test handle_appointment_selection() with 1 dentist auto-selects and skips menu
  - Test handle_appointment_selection() with 2+ dentists shows numbered menu
  - Test handle_dentist_selected() with valid number sets selected_dentist_id and transitions state
  - Test handle_dentist_selected() with invalid number repeats menu
  - Test handle_dentist_selected() with out-of-range number repeats menu
  - Mock: dentist_service, conversation_manager, google_calendar_client
  - Fixtures: create_appointment_router, test_dentists

- [ ] T015 [US1] Create integration test in `tests/integration/test_multi_dentist_booking_flow.py`:
  - Test scenario: 2 dentists available → user selects dentist 1 → user selects slot → user confirms → appointment created
  - Setup: Insert 2 dentists (Hector, Fulano) with real calendar_ids (mocked Google API)
  - Flow: Simulate user messages ("1", "1", "1", "Cleaning") through conversation manager
  - Assertion: Appointment record has correct dentist_id, appears in correct dentist's calendar
  - Test scenario: Concurrent bookings (User A with Dentist 1, User B with Dentist 2, same time slot) → both succeed
  - Test scenario: Concurrent bookings (Both users with same Dentist, same slot) → one succeeds, one fails
  - Use real database (not mocks) per Constitution IV

---

## Phase 4: User Story 2 - Secretary Multi-Calendar Management (P2)

**Goal**: Secretary can view and manage appointments across all dentist calendars.

**Acceptance Criteria**:
1. Secretary selects "2 - Secretaria" from menu
2. Secretary can view appointments for any dentist
3. Secretary can modify/cancel appointments
4. All changes preserve dentist association

**Independent Test**: Can be tested by verifying secretary menu responds to option "2" and displays dentist-specific appointment operations.

**Note**: Full implementation deferred to Release 2. Phase 4 tasks are for initial groundwork.

### Secretary Router Extension (Future)

- [ ] T016 [US2] Extend SecretaryRouter in `src/services/secretary_router.py`:
  - Add method: handle_secretary_menu(session, user_id) → str
    - Return menu options for secretary (placeholder)
    - Prepare for future appointments lookup by dentist
  - Stub implementation that returns "Secretary menu coming soon"
  - Integration with dentist_service to be added in Release 2

### Secretary Tests (Stub)

- [ ] T017 [P] [US2] Create placeholder test in `tests/unit/test_secretary_router.py`:
  - Test secretary menu option returns appropriate message
  - Stub test: verify secretary can access the feature
  - Full implementation blocked by US1 completion

- [ ] T018 [US2] Update integration test to verify secretary option exists:
  - Menu displays "2. Secretaria" option
  - Selecting "2" routes to secretary flow (no-op for now)

- [ ] T019 [US2] Document secretary appointment lookup requirements in `specs/003-multi-dentist-booking/secretary-feature.md`:
  - Query patterns for fetching appointments by dentist
  - Modification workflow design
  - Deferred implementation until Release 2

---

## Phase 5: User Story 3 - Scalable Dentist Configuration (P3)

**Goal**: System maintains configurable dentist list; dentists can be added/removed without code changes.

**Acceptance Criteria**:
1. Dentist added to DB → immediately available in booking menu
2. Dentist removed → no longer appears in menu
3. Dentist calendar_id updated → appointments routed to new calendar
4. No code changes required for dentist roster changes

**Independent Test**: Can be tested by:
- Adding dentist row to DB
- Querying booking menu in bot
- Verifying new dentist appears in selection list
- Removing dentist
- Verifying removed dentist no longer appears

### Dentist CRUD Endpoints (Optional, for Admin Use)

- [ ] T020 [US3] Create optional admin endpoints in `src/api/admin_dentist_api.py` (if external management needed):
  - POST /admin/dentists: Create dentist
  - GET /admin/dentists: List all dentists
  - PUT /admin/dentists/{id}: Update dentist
  - DELETE /admin/dentists/{id}: Deactivate dentist (soft delete via active_status)
  - Requires admin authentication (future: implement access control)
  - OR use direct database management (simpler, recommended for MVP)

### Configuration & Initialization

- [X] T021 [US3] Create dentist seeding script `scripts/seed_dentists.py`:
  - Script accepts dentist name and calendar_id as arguments
  - Inserts dentist into DB via SQLAlchemy
  - Usage: `python scripts/seed_dentists.py "Hector" "hector@clinic.calendar.google.com"`
  - Alternatively: provide SQL insert statements for manual DB operation
  - Document in README with example commands

### Configuration Documentation

- [X] T022 [P] [US3] Document dentist configuration in `README.md` and `SETUP.md`:
  - Section: "Managing Dentists"
  - How to add a new dentist (DB insert or script)
  - How to remove a dentist (soft delete via active_status flag)
  - How to update calendar_id
  - Example dentist records for development/testing
  - Constraint: changes take effect on next bot interaction (no restart needed due to DB queries)

### Tests for User Story 3

- [ ] T023 [P] [US3] Create unit tests in `tests/unit/test_dentist_service.py` (continued):
  - Test get_active_dentists() returns newly added dentist immediately
  - Test get_active_dentists() excludes deactivated dentist
  - Test calendar_id lookup returns correct ID for updated dentist

- [ ] T024 [US3] Create integration test in `tests/integration/test_dentist_configuration.py`:
  - Setup: Start with 2 dentists
  - Test: Add new dentist to DB, refresh menu, verify appears
  - Test: Deactivate dentist, refresh menu, verify disappears
  - Test: Update calendar_id, book appointment, verify correct calendar used
  - Use real database (per Constitution IV)

---

## Phase 6: Polish & Cross-Cutting Concerns

### Documentation & Quality

- [X] T025 Update API documentation and inline comments:
  - Add docstrings to new services: DentistService, extend AppointmentService
  - Add docstrings to new models: Dentist, extend Appointment
  - Add docstrings to new schemas: DentistCreate, DentistResponse
  - Document conversation state changes (SELECTING_DENTIST step)
  - Follow existing docstring style (reStructuredText or Google style per codebase)

### Performance & Caching (Optional)

- [ ] T026 [P] Implement dentist list caching (optional, low priority):
  - Cache get_active_dentists() result for 5 minutes
  - Invalidate on dentist update/delete
  - Use existing caching pattern from project (if any)
  - OR skip for MVP (DB queries are fast with indexes)
  - Decision: Document in [research.md](research.md) performance section

### Migration Execution

- [ ] T027 Run and verify Alembic migration:
  - Pre-deployment: Run `alembic upgrade head` on staging database
  - Verify dentist table created and indexed
  - Verify appointment.dentist_id column added
  - Verify foreign key constraint works
  - Run rollback test: `alembic downgrade -1` and verify rollback succeeds
  - Document rollback procedure in deployment guide

---

## Task Dependencies & Critical Path

```
T001 (Migration)
  ↓
T002 (Structure)
  ↓
T003, T004, T005, T006, T007 (Foundation - can run in parallel)
  ↓
T008 (DentistService)
  ├─→ T009 (AppointmentService)
  │   ├─→ T010 (AppointmentRouter)
  │   │   ├─→ T011 (MenuRouter)
  │   │   │   └─→ T012 (Webhook)
  │   │   │       └─→ T013, T014, T015 (Tests - can run in parallel)
  │   │   └─→ T013, T014, T015 (Tests - can run in parallel)
  │   └─→ T013, T014, T015 (Tests - can run in parallel)
  └─→ T020, T021, T022, T023, T024 (US3 - can start after T008)
      └─→ T016, T017, T018, T019 (US2 - can start early)

T025, T026, T027 (Polish - can happen in parallel or at end)
```

**Critical Path**: T001 → T002 → Foundation → T008 → T009 → T010 → T011 → T012 → Tests

**Parallelizable**: 
- Phase 2: T003, T004, T005, T006, T007 can run in parallel
- User Story 1 tests: T013, T014, T015 can run in parallel
- User Story 2: T016-T019 can start early (separate feature)
- User Story 3: T020-T024 can start after T008
- Polish: T025, T026, T027 can run at end or in parallel

---

## Execution Roadmap (Recommended Order)

### Release 1 (MVP): User Stories P1 + P3

**Week 1**:
1. T001: Create migration
2. T002: Setup structure
3. T003-T007: Foundation components (parallel)
4. T008-T009: Core services

**Week 2**:
5. T010-T012: Router integration
6. T013-T015: Testing
7. T020-T024: Dentist configuration
8. T027: Migration execution

**Week 3**:
9. T025: Documentation
10. T026: Caching (optional)
11. Code review & deployment

### Release 2 (Future): User Story P2

**Post-MVP**:
1. T016-T019: Secretary feature (deferred)
2. Implement full secretary appointment management
3. Secretary can CRUD appointments across all dentists

---

## Format Validation Checklist

- [x] All tasks follow checklist format: `- [ ] [ID] [Markers] Description with file path`
- [x] Task IDs sequential: T001 through T027
- [x] P markers used for parallelizable tasks
- [x] Story labels present for user story phase tasks: [US1], [US2], [US3]
- [x] No story labels on setup/foundation/polish phases
- [x] All tasks have clear file paths
- [x] All tasks are independently executable
- [x] Each user story has independent test criteria
- [x] Dependencies documented in "Task Dependencies" section

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Test Coverage | >80% for new services (DentistService) and models (Dentist) |
| Task Completion | All T001-T015 complete = Release 1 MVP ready |
| Integration Test Pass Rate | 100% of booking flow scenarios with multiple dentists |
| Deployment | Zero-downtime migration; rollback tested and documented |
| Documentation | README updated with dentist configuration instructions |

---

## Related Documentation

- **Specification**: [spec.md](spec.md)
- **Implementation Plan**: [plan.md](plan.md)
- **Data Model**: [data-model.md](data-model.md)
- **Service Contracts**: [contracts/dentist-selection.md](contracts/dentist-selection.md)
- **Research & Decisions**: [research.md](research.md)
- **Quick Implementation Guide**: [quickstart.md](quickstart.md)
