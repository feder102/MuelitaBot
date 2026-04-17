# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

turnoHector is a FastAPI backend that powers a Telegram bot for dental appointment booking and cancellation. It uses a webhook-based architecture: Telegram sends updates to `/webhook`, which drives a per-user conversation state machine stored in PostgreSQL.

## Commands

All commands run from the repo root with the venv active (`source venv/bin/activate`).

```bash
# Run the server (dev mode, auto-reload)
python3 src/main.py

# Run all tests
pytest tests/ -v

# Run a single test file
pytest tests/unit/test_signature_validator.py -v

# Lint
ruff check .

# Format
black src/ tests/
isort src/ tests/

# Database migrations
alembic upgrade head

# Add a dentist to the database
python3 scripts/seed_dentists.py "Dr. Name" "calendar_id@clinic.calendar.google.com"

# Test multi-dentist flow end-to-end
python3 scripts/test_multi_dentist_flow.py
```

## Architecture

### Request Flow

```
Telegram → POST /webhook → signature validation (HMAC-SHA256)
    → WebhookHandler.handle_webhook()
        → MessageParser: extract user_id + text
        → ConversationManager: get/create TelegramUser + ConversationState
        → [branch on ConversationStateEnum]
            → MenuRouter / AppointmentRouter / CancellationRouter
        → TelegramClient.send_message()
        → session.commit()
        → AuditLog entries written throughout
```

### Conversation State Machine

`ConversationStateEnum` (in `src/models/conversation_state.py`) defines all valid states. `WebhookHandler.handle_webhook()` is a large if/elif dispatch on the current state — each branch calls a router method that returns `(new_state, response_message[, context_data])`. The handler then calls `conversation_manager.update_state()` and sends the message.

Key states and their routers:
- `AWAITING_MENU` / `AWAITING_SELECTION` → `MenuRouter`
- `SELECTING_DENTIST` → `AppointmentRouter.handle_dentist_selected()`
- `AWAITING_SLOT_SELECTION` → `AppointmentRouter.validate_slot_selection()`
- `AWAITING_REASON_TEXT` → `AppointmentRouter.validate_and_book_appointment()`
- `SELECTING_CANCELLATION_APPOINTMENT` → `CancellationRouter.validate_appointment_selection()`
- `AWAITING_CANCELLATION_CONFIRMATION` → `CancellationRouter.confirm_and_cancel_appointment()`

Inter-step context (selected dentist UUID, available slots list, selected slot) is persisted in `conversation_state.context_data` (JSONB column), keyed by well-known strings like `"selected_dentist_id"`, `"available_slots"`, `"selected_slot"`.

### Multi-Dentist Routing

Each dentist row in the `dentists` table has its own `calendar_id`. When a user selects a dentist, the UUID is stored in `context_data["selected_dentist_id"]` and carried through subsequent states. `AppointmentRouter` and `CancellationRouter` both read this to target the correct Google Calendar.

The `.env` `GOOGLE_CALENDAR_ID` is a fallback only; the DB value takes precedence.

### Google Calendar Integration

`GoogleCalendarClient` (`src/services/google_calendar_client.py`) wraps the Google Calendar API using a service account. Credentials are stored base64-encoded in `GOOGLE_CALENDAR_CREDENTIALS_B64`. `SlotGenerator` computes free slots from busy periods. Appointment creation returns a `google_event_id` stored in the `appointments` table for later cancellation.

### Database

- Async SQLAlchemy via `asyncpg`
- Migrations managed with Alembic (`migrations/versions/`)
- In development, `main.py` auto-creates tables via `Base.metadata.create_all` on startup
- In production, always run `alembic upgrade head`
- Session injected per request via FastAPI dependency in `src/api/webhook.py`

### Key Environment Variables

```
TELEGRAM_BOT_TOKEN
TELEGRAM_BOT_WEBHOOK_SECRET
DATABASE_URL                        # postgresql+asyncpg://...
GOOGLE_CALENDAR_CREDENTIALS_B64     # base64(service_account_json)
GOOGLE_CALENDAR_ID                  # fallback calendar
CLINIC_TIMEZONE                     # default: America/Argentina/Buenos_Aires
APPOINTMENT_SLOTS_START_TIME        # default: 08:00
APPOINTMENT_SLOTS_END_TIME          # default: 13:00
API_ENV                             # development | production
```

## Feature Specs

Each feature has a full spec under `specs/<NNN>-<name>/`. The spec directory includes `spec.md`, `plan.md`, `tasks.md`, `data-model.md`, and `contracts/`. Read these before implementing changes to a feature.

- `001-webhook-menu`: Base webhook + menu routing
- `002-appointment-booking`: Slot display + Google Calendar event creation
- `003-multi-dentist-booking`: Dentist selection before slot display
- `004-cancel-appointment`: List and cancel booked appointments (current branch)

## Testing

- `pytest` config in `pyproject.toml` with `asyncio_mode = "auto"`
- Test directories: `tests/unit/`, `tests/integration/`, `tests/contract/`, `tests/load/`
- Coverage: `pytest tests/ --cov=src --cov-report=html`
