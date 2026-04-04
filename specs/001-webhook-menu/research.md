# Research: Telegram Webhook Menu Backend

**Completed**: 2026-04-04
**Purpose**: Resolve design decisions and validate technical approach for webhook implementation

---

## 1. Telegram Webhook Integration Pattern

### Research Question
How should we reliably receive and process Telegram messages in FastAPI?

### Decision
Use **python-telegram-bot** library with async support (version 20.0+)

### Rationale
- **Official**: Maintained by Telegram community, recommended approach
- **Async-ready**: Native asyncio support aligns with FastAPI's async paradigm
- **Comprehensive**: Full Bot API coverage, no need for manual HTTP wrapping
- **Battle-tested**: Widely used in production Python bots, security vetted
- **Type-safe**: Type hints available, works well with Pydantic schemas

### Alternatives Considered

| Alternative | Pros | Cons | Rejected Because |
|------------|------|------|------------------|
| Hand-rolled HTTP client | Full control, minimal deps | Manual signature validation, error handling, retry logic | Reimplementing existing wheel; security risk if done incorrectly |
| aiogram library | Russian-maintained, popular | Less documentation, smaller community | python-telegram-bot has better English docs |
| Direct REST API calls | Simple | No SDK benefits, manual request building | More boilerplate, slower development |

### Implementation Notes
- Use `telegram.ext.Application` for webhook setup
- Use `BaseUpdate` handlers for message routing
- Configure with bot token from environment (never hardcoded)

---

## 2. Webhook Signature Validation

### Research Question
How do we prevent spoofed webhooks and ensure requests come from Telegram?

### Decision
Implement **HMAC-SHA256 validation** per Telegram Bot API specification

### Rationale
- **Telegram requirement**: Standard security practice for Telegram webhooks
- **Cryptographically secure**: HMAC-SHA256 prevents tampering
- **Header-based**: X-Telegram-Bot-API-Secret-SHA256 header provided by Telegram
- **Constitution aligned**: Satisfies Security-First Design principle (authentication on all endpoints)

### Algorithm
```
Hash = HMAC_SHA256(bot_token, request_body)
Expected = X-Telegram-Bot-API-Secret-SHA256 header (hex string)
Valid = (Hash == Expected)
```

### Implementation Approach
1. Create `SignatureValidator` utility class
2. Add FastAPI middleware to validate signature before routing
3. Return 403 Forbidden for invalid signatures (security gate)
4. Log failed attempts to audit table for security review

---

## 3. Conversation State Management

### Research Question
How should we track which users have selected which menu option across multiple messages?

### Decision
Store conversation state in **PostgreSQL** with per-user session tracking

### Rationale
- **Persistence required**: FR-007 mandates maintaining context across messages
- **Scalability**: Database supports 100+ concurrent users (SC-006)
- **Audit trail**: Required for FR-008 (audit logging for sensitive operations)
- **Constitution**: Aligns with "Database-as-source-of-truth" principle
- **Reliability**: Durable state survives service restarts

### State Machine Design
```
AWAITING_MENU
  ↓ (user sends initial message)
AWAITING_SELECTION
  ↓ (user selects option 1 or 2)
APPOINTMENT_SELECTED or SECRETARY_SELECTED
  ↓ (handoff to next handler)
COMPLETED or INACTIVE
```

### Schema Design
- **telegram_users**: Store Telegram user metadata (id, first_name, created_at)
- **conversation_state**: Track current state per user (current_state enum, last_interaction timestamp)
- **audit_log**: Immutable log of all interactions (for FR-008 audit requirement)

---

## 4. Concurrent User Support

### Research Question
How can we handle 100+ simultaneous webhook requests without blocking?

### Decision
Use **FastAPI's async/await** with **SQLAlchemy async driver** (asyncpg for PostgreSQL)

### Rationale
- **Non-blocking I/O**: async/await prevents threads from blocking on network/DB calls
- **Efficient concurrency**: FastAPI uses Starlette + uvicorn, built for high concurrency
- **Performance**: Allows <2s response time (SC-001) even under load
- **Constitution**: Aligns with Performance & Scalability principle

### Key Components
- **async FastAPI endpoint**: @app.post("/webhook") async def receive_webhook()
- **async SQLAlchemy**: Use sqlalchemy.ext.asyncio for non-blocking queries
- **async Telegram client**: python-telegram-bot supports async via telegram.ext.Application

### Load Testing Strategy
1. Use Locust or Apache JMeter to simulate 100+ concurrent webhooks
2. Measure response time distribution (target: p95 < 2s)
3. Monitor DB connection pool, CPU usage, memory
4. Identify bottlenecks before production release

---

## 5. Error Handling & Audit Logging

### Research Question
How should we handle errors while maintaining security and enabling compliance auditing?

### Decision
**Structured JSON logging** + **immutable SQL audit tables**

### Rationale
- **Medical data**: PHI requires immutable audit trail per constitution
- **Security**: Detailed logs server-side, vague messages to clients (prevent information leakage)
- **Compliance**: Enable monthly constitution compliance reviews (track all user actions)
- **Debuggability**: Structured logs enable quick diagnosis without breaking security

### Implementation
- **Server-side**: JSON logs with full context (user_id, action, error, stack trace) written to audit_log table
- **Client-side**: Generic error messages ("El servidor no está disponible. Intenta más tarde.") without internals
- **Audit table schema**:
  - user_id (FK to telegram_users)
  - action (WEBHOOK_RECEIVED, MENU_DISPLAYED, SELECTION_MADE, etc.)
  - status (SUCCESS, VALIDATION_FAILED, ERROR)
  - message_text (user input)
  - response_text (bot response)
  - timestamp (UTC)

### Tools
- **python-json-logger**: Structured JSON logging to stdout
- **SQLAlchemy models**: audit_log table for immutable record
- **FastAPI exception handlers**: Convert exceptions to proper HTTP responses + logs

---

## 6. Message Parsing & Validation

### Research Question
How should we extract user intent from Telegram messages, including edge cases?

### Decision
Use **Pydantic schemas** for validation + **simple text parsing** for menu selections

### Rationale
- **Type safety**: Pydantic validates Telegram Update structure before processing
- **Simplicity**: Menu selections are just "1" or "2" (no NLP needed in v1)
- **Extensibility**: Easy to add new menu options or selection methods later
- **Constitution**: Aligns with Clean Code & Simplicity (no over-engineering)

### Parsing Logic
```python
# Normalize user input
normalized = message.text.strip().lower()

# Extract menu selection
selection = None
if normalized in ["1", "opción 1", "option 1"]:
    selection = "appointment"
elif normalized in ["2", "opción 2", "option 2"]:
    selection = "secretary"
else:
    # Invalid selection → re-display menu
    selection = None
```

### Edge Cases Handled
- Whitespace trim
- Case insensitive matching
- Non-ASCII characters (emojis): safely ignored
- Rapid consecutive messages: DB timestamp prevents duplicate processing
- Empty messages: Caught by Pydantic validation

---

## 7. Technology Stack Summary

| Component | Technology | Version | Why |
|-----------|-----------|---------|-----|
| Framework | FastAPI | 0.104+ | Async, automatic OpenAPI docs, Pydantic integration |
| Telegram SDK | python-telegram-bot | 20.0+ | Official, async support, comprehensive |
| ORM | SQLAlchemy | 2.0+ | Async support, type hints, mature ecosystem |
| Database | PostgreSQL | 14+ | ACID compliance, JSON fields for extensibility |
| Async DB | asyncpg | 0.29+ | Fastest async PostgreSQL driver for Python |
| Validation | Pydantic | 2.0+ | Type-safe, automatic docs, pre-installed with FastAPI |
| Testing | pytest | 7.4+ | Industry standard, async support via pytest-asyncio |
| Logging | python-json-logger | 2.0+ | Structured JSON logs for audit trail |
| Hashing | bcrypt | 4.1+ | For future password/token handling |
| Migrations | Alembic | 1.13+ | Database schema versioning and rollback |

---

## Implementation Readiness

✅ **All research questions resolved**
✅ **Technology stack selected and justified**
✅ **Architecture aligns with turnoHector Constitution**
✅ **No blocking unknowns remaining**

**Next step**: Proceed to Phase 1 design (data-model.md, contracts/, quickstart.md)
