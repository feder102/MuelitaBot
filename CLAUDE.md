# turnoHector Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-04-12

## Active Technologies
- Python 3.11+ + FastAPI, SQLAlchemy (async ORM), google-auth, google-api-python-client, python-telegram-bot (002-appointment-booking)
- PostgreSQL (extends existing schema with Appointment table) (002-appointment-booking)
- Python 3.11+ + FastAPI, SQLAlchemy (async ORM), google-api-python-client, python-telegram-bot, Pydantic (003-multi-dentist-booking)
- PostgreSQL (async via asyncpg) (003-multi-dentist-booking)
- Python 3.11+ + FastAPI (async), SQLAlchemy (async ORM), python-telegram-bot (webhook mode), google-api-python-client, Alembic (004-cancel-appointment)

- Python 3.11+ + FastAPI, python-telegram-bot (or async Telegram API client), SQLAlchemy ORM, pydantic (001-webhook-menu)

## Project Structure

```text
backend/
frontend/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.11+: Follow standard conventions

## Recent Changes
- 004-cancel-appointment: Added Python 3.11+ + FastAPI (async), SQLAlchemy (async ORM), python-telegram-bot (webhook mode), google-api-python-client, Alembic
- 003-multi-dentist-booking: Added Python 3.11+ + FastAPI, SQLAlchemy (async ORM), google-api-python-client, python-telegram-bot, Pydantic
- 002-appointment-booking: Added Python 3.11+ + FastAPI, SQLAlchemy (async ORM), google-auth, google-api-python-client, python-telegram-bot


## Multi-Dentist Support - ✅ FULLY OPERATIONAL

### Current Dentists in System
- **Hector** (ID: `<hector_dentist_uuid>`)
  - Calendar: `<hector_calendar_id@group.calendar.google.com>`
  - Status: Active ✅

- **Fulano** (ID: `<fulano_dentist_uuid>`)
  - Calendar: `<fulano_calendar_id@group.calendar.google.com>`
  - Status: Active ✅

### How It Works
1. **Calendar ID Source**: Each dentist has a unique `calendar_id` stored in the database
2. **Slot Fetching**: When user selects a dentist, slots are fetched from THAT dentist's Google Calendar
3. **Event Creation**: When booking, the appointment is created in the correct dentist's calendar (via `calendar_id` from DB)
4. **Database**: Appointments link to specific dentist via `dentist_id` foreign key

### User Flow
- **Single dentist**: Auto-selects, shows slots immediately
- **Multiple dentists**: Shows dentist menu, then slots for selected dentist

### Testing Multi-Dentist Flow
```bash
python3 scripts/test_multi_dentist_flow.py
```
This verifies:
- ✅ Both dentists can be retrieved
- ✅ Slots are fetched from each dentist's calendar
- ✅ Calendar IDs match database values
- ✅ Appointments model supports dentist_id

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
