# Implementation Plan: Telegram Webhook Menu Backend

**Branch**: `001-webhook-menu` | **Date**: 2026-04-04 | **Spec**: [Telegram Webhook Menu Backend](/specs/001-webhook-menu/spec.md)
**Input**: Feature specification from `/specs/001-webhook-menu/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Build a FastAPI-based webhook server that receives messages from Telegram, validates webhook signatures, displays an interactive menu to users, and routes menu selections to appropriate handlers. The system maintains conversation state per user, enforces security-first practices, and handles 100+ concurrent users with sub-2-second response times.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: FastAPI, python-telegram-bot (or async Telegram API client), SQLAlchemy ORM, pydantic  
**Storage**: PostgreSQL (for conversation state, user context, audit logs)  
**Testing**: pytest + pytest-asyncio (for async FastAPI tests)  
**Target Platform**: Linux server (containerized via Docker)
**Project Type**: web-service (RESTful API backend)  
**Performance Goals**: <2 seconds response time per webhook (SC-001), 100+ concurrent users (SC-006), 100% webhook processing success (SC-002)  
**Constraints**: Medical data (PHI) requires encryption at rest/transit (TLS 1.3+), webhook signature validation (HMAC-SHA256), audit logging for compliance  
**Scale/Scope**: Medical center with multiple doctors, extensible to multiple calendars, future WhatsApp integration planned

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Clean Code & Simplicity
- **Gate**: Webhook handler must have single responsibility (validate → parse → route)
- **Gate**: Menu logic must be straightforward, not over-engineered
- **Gate**: No complex abstractions for single-use operations
- **Status**: ✅ PASS - Feature scope is minimal and focused on core functionality

### Principle II: Security-First Design
- **Gate**: HMAC-SHA256 webhook signature validation REQUIRED (FR-002)
- **Gate**: Input validation on all Telegram message data (FR-003)
- **Gate**: Audit logging for all user interactions and selections (FR-008)
- **Gate**: No hardcoded bot token or secrets in code
- **Gate**: TLS 1.3+ for outbound Telegram API calls
- **Gate**: Error messages must not leak system internals
- **Status**: ✅ PASS - All security gates are addressed in functional requirements

### Principle III: Performance & Scalability
- **Gate**: <2 second response time per webhook (SC-001)
- **Gate**: Support 100+ concurrent users without degradation (SC-006)
- **Gate**: Database queries optimized for conversation state lookups
- **Gate**: Load testing required before production release
- **Status**: ✅ PASS - Performance targets defined in spec; implementation will verify via load testing

### Principle IV: Test-First & Reliability
- **Gate**: >80% code coverage required (unit + integration tests)
- **Gate**: Integration tests against real PostgreSQL instance
- **Gate**: Contract tests for webhook interface (input/output schemas)
- **Gate**: All tests must pass before merge; failing tests block deploy
- **Status**: ✅ PASS - Testing strategy will be defined in Phase 1 (data-model + contracts)

### Principle V: Extensibility & Data Integrity
- **Gate**: Conversation state schema must support future menu options without migration
- **Gate**: Menu routing logic should be configurable (not hardcoded)
- **Gate**: Database constraints enforced at schema layer (FK, NOT NULL, UNIQUE)
- **Status**: ✅ PASS - Data model will be designed to support extensibility

## Project Structure

### Documentation (this feature)

```text
specs/001-webhook-menu/
├── spec.md              # Feature specification ✅
├── plan.md              # This file (implementation plan)
├── research.md          # Phase 0 output (research findings)
├── data-model.md        # Phase 1 output (entity definitions)
├── quickstart.md        # Phase 1 output (setup & demo instructions)
├── contracts/           # Phase 1 output (webhook interface contracts)
│   └── telegram_webhook.md
├── checklists/
│   └── requirements.md  # Specification quality validation ✅
└── tasks.md             # Phase 2 output (implementation tasks)
```

### Source Code (repository root)

```text
.
├── src/
│   ├── main.py                    # FastAPI application entry point
│   ├── config.py                  # Configuration (env vars, settings)
│   ├── db.py                      # Database connection and session management
│   ├── models/
│   │   ├── __init__.py
│   │   ├── telegram_user.py       # TelegramUser ORM model
│   │   ├── conversation_state.py  # ConversationState ORM model
│   │   └── message.py             # Message ORM model (audit log)
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── telegram_webhook.py    # Pydantic schemas for webhook request/response
│   │   └── telegram_types.py      # Telegram API type definitions
│   ├── api/
│   │   ├── __init__.py
│   │   └── webhook.py             # POST /webhook endpoint
│   ├── services/
│   │   ├── __init__.py
│   │   ├── webhook_handler.py     # Webhook processing logic
│   │   ├── message_parser.py      # Parse incoming Telegram messages
│   │   ├── menu_router.py         # Route menu selections to appropriate flow
│   │   └── conversation_manager.py # Manage user conversation state
│   └── utils/
│       ├── __init__.py
│       ├── telegram_client.py     # Wrapper for Telegram Bot API
│       ├── signature_validator.py # HMAC-SHA256 webhook signature validation
│       └── logger.py              # Structured logging with audit trail
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # pytest fixtures and configuration
│   ├── unit/
│   │   ├── test_signature_validator.py
│   │   ├── test_message_parser.py
│   │   ├── test_menu_router.py
│   │   └── test_conversation_manager.py
│   ├── integration/
│   │   ├── test_webhook_handler.py      # Full webhook flow with real DB
│   │   └── test_conversation_state.py   # State persistence and retrieval
│   └── contract/
│       └── test_telegram_webhook.py     # Schema validation for webhook
├── migrations/
│   ├── env.py                     # Alembic configuration
│   ├── script.py.mako
│   └── versions/
│       └── 001_initial_schema.py  # Create user, state, message tables
├── requirements.txt               # Python dependencies
├── requirements-dev.txt           # Dev dependencies (pytest, etc.)
├── .env.example                   # Example environment variables
├── docker-compose.yml             # Local PostgreSQL for development
├── Dockerfile                     # Container image for deployment
└── README.md                      # Project setup and usage
```

**Structure Decision**: Single FastAPI web-service backend (Option 1). This feature is backend-only with no frontend component. Structure supports clean separation between API routes, business logic, data models, and utilities. Tests organized by type (unit/integration/contract) following constitution requirements for >80% coverage and real-database integration testing.

## Complexity Tracking

> No constitution violations identified. All gates passed. No complexity justification required.

---

## Phase 0: Research & Clarifications

### Research Tasks Completed

1. **Telegram Webhook Integration Pattern**
   - Decision: Use official `python-telegram-bot` library (async support via `telegram.ext`)
   - Rationale: Well-maintained, comprehensive API coverage, active community, async support for FastAPI
   - Alternatives considered: Hand-rolled HTTP client (too manual), `aiogram` (less docs), REST API client (missing abstractions)

2. **Webhook Signature Validation**
   - Decision: Implement HMAC-SHA256 validation per Telegram's spec (X-Telegram-Bot-API-Secret-SHA256 header)
   - Rationale: Standard for Telegram bots, cryptographically secure, prevents spoofing
   - Implementation: Pre-request middleware to validate all incoming webhooks before routing

3. **Conversation State Management**
   - Decision: Store in PostgreSQL with per-user session tracking
   - Rationale: Persistent storage required (FR-007), supports concurrent users (FR-010), audit logging (FR-008)
   - Schema: `telegram_users` (id, user_id, state, created_at, updated_at), `conversation_state` (user_id, current_menu, last_interaction, FK to users)

4. **Concurrency & Performance**
   - Decision: Use FastAPI's async/await + SQLAlchemy async driver
   - Rationale: Non-blocking I/O enables 100+ concurrent users, leverages asyncio for <2s response time
   - Verification: Load testing with Locust to validate SC-001, SC-006

5. **Error Handling & Logging**
   - Decision: Structured JSON logging (python-json-logger) + SQL audit tables
   - Rationale: Medical data requires immutable audit trail, enables compliance review, debug visibility
   - Implementation: Every webhook + user action logged to `audit_log` table with timestamp, user_id, action, result

---

## Phase 1: Design & Contracts

### Entity Definitions (data-model.md)

**TelegramUser**
- id: UUID (primary key)
- telegram_user_id: bigint (unique, from Telegram API)
- first_name: string
- last_name: string (nullable)
- username: string (nullable)
- is_active: boolean (soft delete flag)
- created_at: datetime (UTC)
- updated_at: datetime (UTC)

**ConversationState**
- user_id: UUID (FK → TelegramUser.id)
- current_state: enum (AWAITING_MENU, APPOINTMENT_SELECTED, SECRETARY_SELECTED, INACTIVE)
- last_interaction: datetime (UTC)
- menu_display_count: int (track re-displays for UX)
- metadata: jsonb (extensible for future state data)

**AuditLog**
- id: UUID (primary key)
- user_id: UUID (FK → TelegramUser.id, nullable for failed auth)
- action: string (WEBHOOK_RECEIVED, MENU_DISPLAYED, SELECTION_MADE, etc.)
- status: enum (SUCCESS, VALIDATION_FAILED, ERROR)
- message_text: string (the user's input)
- response_text: string (the bot's response)
- ip_address: string (for security review)
- created_at: datetime (UTC)

### Webhook Contract (contracts/telegram_webhook.md)

**Request**
- Header: `X-Telegram-Bot-API-Secret-SHA256` (signature validation)
- Body: JSON object from Telegram Update API
  - update_id: int
  - message: object with {message_id, date, chat: {id, type, first_name}, text}

**Response**
- HTTP 200 OK
- Body: { "ok": true } (acknowledges receipt; bot sends reply separately via API)

**Expected Flows**
1. Valid webhook → menu displayed
2. Invalid signature → 403 Forbidden (no processing)
3. Menu selection → route to handler + acknowledgment

### Quickstart Instructions (quickstart.md)

1. Setup PostgreSQL (docker-compose up)
2. Create .env with TELEGRAM_BOT_TOKEN (from BotFather)
3. Install dependencies: pip install -r requirements.txt
4. Run migrations: alembic upgrade head
5. Start server: uvicorn src.main:app --reload
6. Test: Send message to bot → verify menu response in console logs

---

## Phase 1 Complete: Ready for Phase 2 (Tasks)
