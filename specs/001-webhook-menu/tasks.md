---
description: "Implementation tasks for Telegram Webhook Menu Backend"
---

# Tasks: Telegram Webhook Menu Backend

**Input**: Design documents from `/specs/001-webhook-menu/`  
**Prerequisites**: plan.md ✅, spec.md ✅, data-model.md ✅, research.md ✅, contracts/ ✅, quickstart.md ✅

**Tests**: Contract tests, integration tests, and unit tests included (test-first approach per turnoHector Constitution IV)

**Organization**: Tasks grouped by user story to enable independent implementation and testing of each story.

---

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Single project: `src/`, `tests/` at repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create project structure per implementation plan (directories: src/, tests/, migrations/, .github/)
- [x] T002 Initialize Python 3.11+ project with pyproject.toml or requirements.txt (FastAPI, SQLAlchemy, python-telegram-bot, pytest, etc.)
- [x] T003 [P] Setup linting tools (black, flake8, isort) and formatting configuration (.flake8, pyproject.toml)
- [x] T004 [P] Create Dockerfile and docker-compose.yml for local PostgreSQL development
- [x] T005 [P] Initialize Git repository and create .gitignore (exclude .env, __pycache__, venv/)
- [x] T006 Create .env.example template with all required environment variables (TELEGRAM_BOT_TOKEN, DATABASE_URL, etc.)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T007 [P] Setup database connection pool and SQLAlchemy async driver configuration in src/db.py
- [x] T008 [P] Create application settings and configuration management in src/config.py (load from .env)
- [x] T009 [P] Create signature validation utility class in src/utils/signature_validator.py (HMAC-SHA256 for Telegram webhooks)
- [x] T010 [P] Setup structured logging infrastructure in src/utils/logger.py (JSON logs + audit trail)
- [x] T011 [P] Initialize FastAPI application entry point in src/main.py (async app, middleware setup)
- [x] T012 Create Alembic migration framework (alembic init migrations, configure env.py)
- [x] T013 Create initial database schema migration in migrations/versions/001_initial_schema.py (TelegramUser, ConversationState, AuditLog tables with indexes)
- [x] T014 [P] Create ORM base model and database session management in src/models/__init__.py
- [ ] T015 Create Pydantic response schemas for API errors in src/schemas/error.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - User Receives Menu From Bot (Priority: P1) 🎯 MVP

**Goal**: User sends message to bot → bot displays interactive menu with 2 options (appointment + secretary)

**Independent Test**: Can be fully tested by sending a message to the bot webhook endpoint and verifying menu response. Delivers immediate user engagement and demonstrates bot's core capability.

### Contract Tests for User Story 1 (REQUIRED - test-first per Constitution)

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T016 [P] [US1] Contract test: Valid webhook with signature returns 200 OK in tests/contract/test_telegram_webhook.py
- [ ] T017 [P] [US1] Contract test: Invalid webhook signature returns 403 Forbidden in tests/contract/test_telegram_webhook.py
- [ ] T018 [P] [US1] Contract test: Malformed JSON returns 400 Bad Request in tests/contract/test_telegram_webhook.py
- [ ] T019 [P] [US1] Integration test: Complete webhook flow (receive → validate → parse → display menu) in tests/integration/test_webhook_handler.py

### ORM Models for User Story 1

- [x] T020 [P] [US1] Create TelegramUser ORM model with fields (id, telegram_user_id, first_name, last_name, username, is_active, created_at, updated_at) in src/models/telegram_user.py
- [x] T021 [P] [US1] Create ConversationState ORM model with fields (user_id FK, current_state ENUM, last_interaction, menu_display_count, metadata JSONB) in src/models/conversation_state.py
- [x] T022 [P] [US1] Create AuditLog ORM model with fields (id, user_id, action, status, message_text, response_text, error_detail, ip_address, created_at) in src/models/audit_log.py

### Pydantic Schemas for User Story 1

- [x] T023 [P] [US1] Create Telegram webhook request/response Pydantic schemas in src/schemas/telegram_webhook.py (Update, Message, Chat, User objects)
- [x] T024 [P] [US1] Create Telegram API type definitions in src/schemas/telegram_types.py (enums for conversation states, action types)

### Services and Utilities for User Story 1

- [x] T025 [US1] Implement message parser service in src/services/message_parser.py (extract user_id, message text, handle encoding)
- [x] T026 [US1] Implement conversation manager service in src/services/conversation_manager.py (lookup/create user, get/update state)
- [x] T027 [US1] Implement webhook handler service in src/services/webhook_handler.py (orchestrate: validate → parse → get user → update state → send menu)
- [x] T028 [US1] Create Telegram Bot API client wrapper in src/utils/telegram_client.py (send message via Telegram API)
- [x] T029 [US1] Implement database session and transaction management for webhook processing

### API Endpoint for User Story 1

- [x] T030 [US1] Create POST /webhook endpoint in src/api/webhook.py (FastAPI route, signature validation middleware, error handling)

### Unit Tests for User Story 1

- [ ] T031 [P] [US1] Unit test: Signature validation accepts valid signatures in tests/unit/test_signature_validator.py
- [ ] T032 [P] [US1] Unit test: Signature validation rejects invalid signatures in tests/unit/test_signature_validator.py
- [ ] T033 [P] [US1] Unit test: Message parser extracts user_id and text correctly in tests/unit/test_message_parser.py
- [ ] T034 [P] [US1] Unit test: Message parser handles edge cases (special chars, emojis, empty) in tests/unit/test_message_parser.py
- [ ] T035 [P] [US1] Unit test: Conversation manager creates new user correctly in tests/unit/test_conversation_manager.py
- [ ] T036 [P] [US1] Unit test: Conversation manager retrieves existing user state in tests/unit/test_conversation_manager.py
- [ ] T037 [P] [US1] Unit test: Menu display message formatted correctly in Spanish in tests/unit/test_webhook_handler.py

### Integration Tests for User Story 1

- [ ] T038 [US1] Integration test: Menu displayed for new user in tests/integration/test_webhook_handler.py (full flow: webhook → menu)
- [ ] T039 [US1] Integration test: Menu re-displayed for invalid selection in tests/integration/test_webhook_handler.py
- [ ] T040 [US1] Integration test: User state persisted to database across multiple messages in tests/integration/test_conversation_persistence.py

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently. Menu displays correctly to new users.

---

## Phase 4: User Story 2 - User Selects Appointment Request (Priority: P2)

**Goal**: User selects "1: Solicitar turno" → system acknowledges selection and transitions to appointment flow

**Independent Test**: Can be tested by selecting menu option 1 and verifying system acknowledges selection and state transitions correctly. Delivers core business value (appointment booking).

### Contract Tests for User Story 2

- [ ] T041 [P] [US2] Contract test: Menu selection "1" is recognized in tests/contract/test_menu_selection.py
- [ ] T042 [P] [US2] Contract test: Appointment selection triggers correct response in tests/contract/test_menu_selection.py

### Services for User Story 2

- [x] T043 [US2] Create menu router service in src/services/menu_router.py (route selections: "1" → appointment, "2" → secretary)
- [x] T044 [US2] Implement appointment selection handler in src/services/menu_router.py (acknowledge, set state to APPOINTMENT_SELECTED)
- [x] T045 [US2] Update conversation manager to support state transitions (AWAITING_SELECTION → APPOINTMENT_SELECTED)
- [x] T046 [US2] Update webhook handler to detect and route menu selections (depends on T030, T043)

### Unit Tests for User Story 2

- [ ] T047 [P] [US2] Unit test: Menu router correctly identifies "1" as appointment selection in tests/unit/test_menu_router.py
- [ ] T048 [P] [US2] Unit test: Menu router handles invalid selections by returning None in tests/unit/test_menu_router.py
- [ ] T049 [P] [US2] Unit test: Appointment acknowledgment message is correct in Spanish in tests/unit/test_menu_router.py
- [ ] T050 [P] [US2] Unit test: State transition from AWAITING_SELECTION to APPOINTMENT_SELECTED works in tests/unit/test_conversation_manager.py

### Integration Tests for User Story 2

- [ ] T051 [US2] Integration test: User selects "1", state transitions to APPOINTMENT_SELECTED in tests/integration/test_appointment_selection.py
- [ ] T052 [US2] Integration test: Appointment acknowledgment sent to user in tests/integration/test_appointment_selection.py
- [ ] T053 [US2] Integration test: Invalid selection re-displays menu without state change in tests/integration/test_appointment_selection.py
- [ ] T054 [US2] Integration test: Concurrent users selecting appointment don't interfere in tests/integration/test_concurrent_selections.py

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently. Users can view menu AND select appointment option.

---

## Phase 5: User Story 3 - User Selects Secretary Contact (Priority: P3)

**Goal**: User selects "2: Hablar con secretaria" → system acknowledges selection and provides secretary contact info

**Independent Test**: Can be tested by selecting menu option 2 and verifying system acknowledges selection and provides contact info. Delivers user support capability (secretary fallback).

### Contract Tests for User Story 3

- [ ] T055 [P] [US3] Contract test: Menu selection "2" is recognized in tests/contract/test_menu_selection.py
- [ ] T056 [P] [US3] Contract test: Secretary selection triggers correct response in tests/contract/test_menu_selection.py

### Services for User Story 3

- [x] T057 [US3] Implement secretary selection handler in src/services/menu_router.py (acknowledge, set state to SECRETARY_SELECTED, provide contact info)
- [x] T058 [US3] Create secretary contact information service in src/services/secretary_service.py (retrieve contact details, formatting)
- [x] T059 [US3] Update webhook handler to route secretary selections (depends on T046, T057)

### Unit Tests for User Story 3

- [ ] T060 [P] [US3] Unit test: Menu router correctly identifies "2" as secretary selection in tests/unit/test_menu_router.py
- [ ] T061 [P] [US3] Unit test: Secretary acknowledgment message is correct in Spanish in tests/unit/test_menu_router.py
- [ ] T062 [P] [US3] Unit test: State transition from AWAITING_SELECTION to SECRETARY_SELECTED works in tests/unit/test_conversation_manager.py
- [ ] T063 [P] [US3] Unit test: Secretary contact information is properly formatted in tests/unit/test_secretary_service.py

### Integration Tests for User Story 3

- [ ] T064 [US3] Integration test: User selects "2", state transitions to SECRETARY_SELECTED in tests/integration/test_secretary_selection.py
- [ ] T065 [US3] Integration test: Secretary contact information sent to user in tests/integration/test_secretary_selection.py
- [ ] T066 [US3] Integration test: Concurrent users selecting secretary don't interfere in tests/integration/test_concurrent_selections.py

**Checkpoint**: All user stories should now be independently functional. Users can: 1) View menu, 2) Select appointment, 3) Select secretary contact.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories, testing, and deployment readiness

- [ ] T067 [P] Write comprehensive load test with Locust (100+ concurrent users, validate SC-001 <2s response, SC-006 100+ users) in tests/load/load_test.py
- [ ] T068 [P] Test database migration rollback procedures (rollback from v001, verify schema cleaned up)
- [ ] T069 [P] Security audit: review code for SQL injection, XSS, credential leaks, verify no secrets in git history
- [ ] T070 [P] Calculate and verify code coverage >80% (run pytest --cov=src, generate report)
- [ ] T071 [P] Add comprehensive docstrings and inline comments to all services and utilities
- [ ] T072 Add API documentation (OpenAPI/Swagger docs at /docs endpoint, describe all endpoints)
- [ ] T073 Run full quickstart.md validation end-to-end (local setup, test with real bot)
- [ ] T074 [P] Performance optimization: review database query indexes, cache frequently accessed data if needed
- [ ] T075 [P] Add database monitoring (slow query logs, connection pool status) to logging
- [ ] T076 Create Docker image and verify containerization works (docker build, docker run)
- [ ] T077 Setup CI/CD pipeline (.github/workflows) to run tests on every push
- [ ] T078 Create deployment guide (docs/deployment.md) for production setup
- [ ] T079 Add health check endpoint (/health) for monitoring
- [ ] T080 Setup monitoring and alerting (optional: Prometheus/Grafana for production)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - **BLOCKS all user stories**
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - **No dependencies on other stories** - Blocks US2 and US3 (menu must exist before selection)
- **User Story 2 (P2)**: Depends on US1 completion - Can start after US1 menu works
- **User Story 3 (P3)**: Depends on US1 completion - Can start after US1 menu works, can run in parallel with US2

### Within Each User Story

- Tests (contracts) MUST be written first and FAIL before implementation (test-first per Constitution IV)
- Models before services
- Services before endpoints
- Core implementation before integration tests
- All tests must PASS before moving to next user story
- Story complete before moving to next priority

### Parallel Opportunities

- **Phase 1**: All [P] tasks can run in parallel (different files, no dependencies)
- **Phase 2**: All [P] tasks can run in parallel within Phase 2 (DB config, logging, utilities)
- **Within US1**: All contract tests [P], all models [P], all schemas [P], all unit tests [P] can run in parallel
- **Between US2 & US3**: Can work on both in parallel after US1 complete (separate handlers, separate tests)

**Parallel Example: User Story 1**

```bash
# Launch all contract tests together:
Task: T016 Contract test: Valid webhook
Task: T017 Contract test: Invalid signature
Task: T018 Contract test: Malformed JSON
Task: T019 Integration test: Complete flow

# Launch all ORM models together:
Task: T020 TelegramUser model
Task: T021 ConversationState model
Task: T022 AuditLog model

# Launch all unit tests together (after services created):
Task: T031 Signature validation tests
Task: T032 Signature validation edge cases
Task: T033 Message parser tests
Task: T034 Message parser edge cases
...
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

Fastest path to a working feature:

1. Complete Phase 1: Setup ✅
2. Complete Phase 2: Foundational ✅ (CRITICAL - blocks everything)
3. Complete Phase 3: User Story 1 ✅
   - Write contract tests first
   - Create ORM models and schemas
   - Implement services
   - Create webhook endpoint
   - Write unit + integration tests
4. **STOP and VALIDATE**: Test User Story 1 independently
   - Send test message to bot via ngrok
   - Verify menu displays correctly
   - Check database records in audit_log
5. Deploy/demo if ready

**Time estimate**: 2-3 days for a solo developer

### Incremental Delivery

Build and release each user story independently:

1. Complete Setup + Foundational → Foundation ready (1 day)
2. Add User Story 1 → Test independently → Deploy/Demo (MVP! Core value) (1-2 days)
3. Add User Story 2 → Test independently → Deploy/Demo (appointment selection) (1 day)
4. Add User Story 3 → Test independently → Deploy/Demo (secretary contact) (1 day)
5. Add Polish phase → Full production-ready release (1-2 days)

**Key benefit**: Each story adds value without breaking previous stories. Can get feedback from users after each release.

### Parallel Team Strategy

With 3 developers:

1. Team completes Setup + Foundational together (1 day)
2. Once Foundational is done:
   - **Developer A**: User Story 1 (menu display) - blocks the others, must be first
   - **Developer B**: Waits for US1 complete, then takes User Story 2 (appointment selection)
   - **Developer C**: Waits for US1 complete, then takes User Story 3 (secretary contact) - can work in parallel with Developer B
3. All stories complete and integrate independently
4. Team comes together for Polish phase (load testing, security review, deployment)

**Parallelization**: Start with Dev A on US1 (2-3 days), then Dev B & C can work on US2 & US3 simultaneously.

---

## Test Coverage Goals

Per turnoHector Constitution Principle IV (Test-First & Reliability):

- **Unit tests**: >80% code coverage (all business logic, edge cases)
- **Integration tests**: All user workflows end-to-end
- **Contract tests**: Webhook interface (valid/invalid signatures, malformed input)
- **Load tests**: Concurrent user simulation (100+ users, <2s response time)

**Verification**:
```bash
pytest tests/ --cov=src --cov-report=html  # Generate coverage report
open htmlcov/index.html  # View details, ensure >80%
```

---

## Notes

- [P] tasks = different files, no dependencies within phase
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- **Test-first approach**: Write tests BEFORE implementation (per Constitution)
- Tests must FAIL before you implement (red-green-refactor cycle)
- Commit after each task or logical group (keep commits atomic)
- Stop at any checkpoint to validate story independently
- Edge cases from spec must be covered in tests (special chars, emojis, rapid messages, DB unavailability, signature failure)

---

## Success Metrics (From spec.md)

| Metric | Target | How to Verify |
|--------|--------|---------------|
| SC-001: Response time | <2 seconds | Load test: measure p95 latency |
| SC-002: Webhook success rate | 100% of valid | Integration tests verify all valid webhooks processed |
| SC-003: Menu display | Clear, readable | Manual test in Telegram app |
| SC-004: Menu selection UX | 95% first/second attempt | Monitor in production, measure user retry rate |
| SC-005: Invalid signature handling | 100% rejected | Contract test: verify 403 on bad signature |
| SC-006: Concurrent users | 100+ without issues | Load test: simulate 100+ concurrent webhooks |
| SC-007: Menu routing | 100% correct routing | Integration tests verify all selections routed |
