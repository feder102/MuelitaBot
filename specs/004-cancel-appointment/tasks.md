# Tasks: Cancel Appointment

**Input**: Design documents from `/specs/004-cancel-appointment/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths included in all descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify branch and existing test suite are green before any changes.

- [x] T001 Confirm active branch is `004-cancel-appointment` and run `cd src && pytest` — all existing tests must pass before any work begins

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schema changes, migration, and low-level service additions that ALL user stories depend on. No user story work can begin until this phase is complete.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T002 Add `google_event_id = Column(String(255), nullable=True, index=True)` to `Appointment` model in `src/models/appointment.py`
- [x] T003 [P] Add `SELECTING_CANCELLATION_APPOINTMENT` and `AWAITING_CANCELLATION_CONFIRMATION` values to `ConversationStateEnum` in `src/models/conversation_state.py`
- [x] T004 Create Alembic migration adding `google_event_id` column to `appointments` table and the two new enum values to `conversationstateenum` — file in `migrations/versions/005_add_google_event_id_and_cancel_states.py`
- [x] T005 Add `async def delete_event(self, calendar_id: str, event_id: str) -> None` to `GoogleCalendarClient` in `src/services/google_calendar_client.py`; catch `HttpError 404` (log warning, do not raise); raise on all other HTTP errors
- [x] T006 In `src/services/appointment_service.py`, after `create_event()` returns, save `google_event.get('id')` to `appointment.google_event_id` before the session flush — fixes the currently discarded event ID
- [x] T007 [P] Extend `MessageParser` in `src/services/message_parser.py` to recognize: `"3"` and `"cancelar turno"` → `"3"`; `"si"` / `"sí"` / `"yes"` → `"si"`; `"no"` / `"volver"` → `"no"` (case-insensitive, strip whitespace)

**Checkpoint**: Migration applied, `google_event_id` column exists, new enum values present, `delete_event()` implemented, event ID saved on booking, message parser updated. Run `cd src && pytest` — all existing tests must still pass.

---

## Phase 3: User Story 1 — Cancel Single Upcoming Appointment (Priority: P1) 🎯 MVP

**Goal**: A patient with one upcoming appointment selects "Cancelar turno", sees their appointment, confirms, and it is removed from DB and Google Calendar.

**Independent Test**: A test user with exactly one future PENDING appointment can complete the full cancel flow end-to-end: option 3 → appointment displayed → "si" → appointment marked CANCELLED, calendar event deleted, success message returned.

### Tests for User Story 1 ⚠️ Write FIRST — verify they FAIL before implementing

- [ ] T008 [P] [US1] Write unit tests for `CancellationRouter.handle_cancellation_request()` (single appointment path) and `confirm_and_cancel_appointment()` ("si" / "no" branches, already-cancelled race condition) in `tests/unit/test_cancellation_router.py` — must FAIL before T011
- [ ] T009 [P] [US1] Write integration test for the full single-appointment cancellation flow (menu → list → confirm → cancelled status → calendar delete called) in `tests/integration/test_cancel_appointment_flow.py` — must FAIL before T011

### Implementation for User Story 1

- [x] T010 [US1] Create `src/services/cancellation_router.py` with `CancellationRouter` class: implement `handle_cancellation_request()` (query upcoming PENDING appointments with `joinedload(Appointment.dentist)`, store list in `context_data`, send numbered list message or empty-state message, transition state) and `confirm_and_cancel_appointment()` (parse "si"/"no", execute atomic `UPDATE ... WHERE patient_user_id = :user AND status = PENDING`, call `calendar_client.delete_event()` if `google_event_id` is set, write `AuditLog` entry, send success/abort message, reset to `AWAITING_MENU`)
- [x] T011 [US1] Add `"3️⃣ Cancelar turno"` to main menu text and route option `"3"` in `src/services/menu_router.py`
- [x] T012 [US1] Wire option `"3"` (at `AWAITING_MENU` state) and `AWAITING_CANCELLATION_CONFIRMATION` state branches to `CancellationRouter` in `src/services/webhook_handler.py`

**Checkpoint**: Run `cd src && pytest tests/unit/test_cancellation_router.py tests/integration/test_cancel_appointment_flow.py` — all Phase 3 tests must PASS. User Story 1 is fully functional and independently testable.

---

## Phase 4: User Story 2 — Select and Cancel One of Multiple Appointments (Priority: P2)

**Goal**: A patient with two or more upcoming appointments sees a numbered list, picks one, confirms, and only that appointment is removed.

**Independent Test**: A test user with 2+ future PENDING appointments (different dentists/dates) completes the cancel flow: option 3 → numbered list displayed → sends "2" → confirmation prompt for appointment 2 → "si" → only appointment 2 is CANCELLED, the others remain PENDING.

### Tests for User Story 2 ⚠️ Write FIRST — verify they FAIL before implementing

- [ ] T013 [P] [US2] Extend `tests/unit/test_cancellation_router.py` with tests for `validate_appointment_selection()`: valid index in range, out-of-range number, non-numeric input, boundary values (index 1 and N)
- [ ] T014 [P] [US2] Extend `tests/integration/test_cancel_appointment_flow.py` with multi-appointment test: 2 appointments exist, select index 2, confirm, verify only index-2 appointment is CANCELLED and index-1 stays PENDING

### Implementation for User Story 2

- [x] T015 [US2] Implement `validate_appointment_selection()` in `src/services/cancellation_router.py`: parse text as integer, validate bounds against `context_data["cancellable_appointments"]` list, send error message on invalid input (state stays `SELECTING_CANCELLATION_APPOINTMENT`), on valid input store selected appointment in `context_data` and transition to `AWAITING_CANCELLATION_CONFIRMATION`
- [x] T016 [US2] Wire `SELECTING_CANCELLATION_APPOINTMENT` state branch to `CancellationRouter.validate_appointment_selection()` in `src/services/webhook_handler.py`

**Checkpoint**: Run full test suite — User Stories 1 AND 2 must both pass. Verify a patient with 2 appointments can cancel the correct one without affecting the other.

---

## Phase 5: User Story 3 — No Upcoming Appointments (Priority: P3)

**Goal**: A patient with no future appointments sees a friendly informational message and is returned to the main menu — no blank screen or error.

**Independent Test**: A test user with zero future PENDING appointments selects option 3, receives the empty-state message in Spanish, and their conversation state returns to `AWAITING_MENU`.

### Tests for User Story 3 ⚠️ Write FIRST — verify they FAIL before implementing

- [ ] T017 [P] [US3] Extend `tests/unit/test_cancellation_router.py` with test for `handle_cancellation_request()` empty-state path: mock DB returns empty list → verify empty-state message sent, state set to `AWAITING_MENU`

### Implementation for User Story 3

- [x] T018 [US3] In `src/services/cancellation_router.py`, add the empty-state branch inside `handle_cancellation_request()`: when query returns zero appointments, send `"No tenés turnos próximos para cancelar."` followed by the main menu, and transition state back to `AWAITING_MENU`

**Checkpoint**: Run full test suite — all three user stories pass. Verify a patient with no appointments gets a friendly message and is not stuck in a broken state.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validate constitution requirements and add test coverage for supporting changes made in the Foundational phase.

- [ ] T019 [P] Write unit tests for the new `MessageParser` inputs (`"3"`, `"cancelar turno"`, `"si"`, `"sí"`, `"no"`, `"volver"`) in `tests/unit/test_message_parser.py`
- [ ] T020 [P] Write unit tests for `GoogleCalendarClient.delete_event()`: successful delete, 404 (already deleted — expect no exception), other HTTP error (expect raise) in `tests/unit/test_google_calendar_client.py`
- [ ] T021 [P] Write unit test for `appointment_service.book_appointment()` verifying that `google_event_id` is saved to the `Appointment` record after booking in `tests/unit/test_appointment_service.py`
- [ ] T022 Run full test suite `cd src && pytest` with coverage — verify >80% coverage on `cancellation_router.py`; fix any gaps before merge

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — BLOCKS all user stories
- **Phase 3 (US1)**: Depends on Phase 2 completion — no dependency on US2 or US3
- **Phase 4 (US2)**: Depends on Phase 3 completion (extends `CancellationRouter`)
- **Phase 5 (US3)**: Depends on Phase 3 completion (extends `handle_cancellation_request`)
- **Phase 6 (Polish)**: Depends on all user story phases being complete

### Within Phase 2

- T002 and T003 are independent (different files) → run in parallel
- T004 depends on nothing → parallel with T002/T003
- T005 depends on T002 (`google_event_id` column must exist in model first)
- T006 (MessageParser) is independent → parallel with T002–T005
- T004 (migration) should run after T002 and T003 (model changes must be in place first)

### Within Each User Story Phase

1. Write tests first (T008/T009, T013/T014, T017) → verify they FAIL
2. Implement (T010, T011, T012 for US1; T015, T016 for US2; T018 for US3)
3. Verify tests now PASS
4. Run full suite to check for regressions

### Parallel Opportunities

```
Phase 2 parallel batch:
  T002 (appointment.py)  +  T003 (conversation_state.py)  +  T004 can start  +  T007 (message_parser.py)
  T005 (appointment_service.py) — after T002 completes

Phase 3 parallel batch:
  T008 (unit tests, write first)  +  T009 (integration tests, write first)
  T010 + T011 — after tests written (CancellationRouter + MenuRouter are different files)
  T012 (webhook_handler.py) — after T010 and T011 complete

Phase 4 parallel batch:
  T013 (unit tests)  +  T014 (integration tests) — write first
  T015 + T016 — after tests written (same file CancellationRouter + webhook_handler.py)

Phase 6 parallel batch:
  T019 + T020 + T021 — independent test files, all parallel
```

---

## Parallel Example: Phase 2 Foundational

```
# Start these together (different files, no dependencies between them):
Task A: T002 — Add google_event_id to src/models/appointment.py
Task B: T003 — Add new enum values to src/models/conversation_state.py
Task C: T007 — Extend MessageParser in src/services/message_parser.py
Task D: T005 — Add delete_event() to src/services/google_calendar_client.py

# After T002 completes:
Task E: T006 — Save google_event_id in src/services/appointment_service.py

# After T002 + T003 complete:
Task F: T004 — Create and run Alembic migration
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002–T007) — CRITICAL
3. Write tests T008–T009 first (verify FAIL)
4. Implement T010–T012
5. **STOP and VALIDATE**: A patient with one upcoming appointment can cancel it end-to-end
6. Demo / deploy if accepted

### Incremental Delivery

1. Setup + Foundational → system is migration-safe, event IDs stored going forward
2. US1 (Phase 3) → single appointment cancel works → **MVP shipped**
3. US2 (Phase 4) → multi-appointment selection works
4. US3 (Phase 5) → graceful empty state handled
5. Polish (Phase 6) → full test coverage verified

---

## Notes

- [P] tasks operate on different files — no merge conflicts when run in parallel
- Tests MUST be written before implementation and verified to FAIL first (constitution: TDD discipline)
- Integration tests must run against a real database — no mocking the DB (constitution requirement)
- All queries in `CancellationRouter` must use `joinedload(Appointment.dentist)` — no N+1 queries
- The `UPDATE ... WHERE patient_user_id = :user AND status = PENDING` guard is the security boundary — do not weaken it
- Appointments with `google_event_id = NULL` (pre-migration): skip calendar delete, log warning, proceed with DB cancellation
- Commit after each task or logical group with a meaningful message
- Stop at each phase checkpoint to validate story independently before continuing
