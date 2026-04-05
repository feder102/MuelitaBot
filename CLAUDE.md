# turnoHector Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-04-05

## Active Technologies
- Python 3.11+ + FastAPI, SQLAlchemy (async ORM), google-auth, google-api-python-client, python-telegram-bot (002-appointment-booking)
- PostgreSQL (extends existing schema with Appointment table) (002-appointment-booking)
- Python 3.11+ + FastAPI, SQLAlchemy (async ORM), google-api-python-client, python-telegram-bot, Pydantic (003-multi-dentist-booking)
- PostgreSQL (async via asyncpg) (003-multi-dentist-booking)

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
- 003-multi-dentist-booking: Added Python 3.11+ + FastAPI, SQLAlchemy (async ORM), google-api-python-client, python-telegram-bot, Pydantic
- 002-appointment-booking: Added Python 3.11+ + FastAPI, SQLAlchemy (async ORM), google-auth, google-api-python-client, python-telegram-bot

- 001-webhook-menu: Added Python 3.11+ + FastAPI, python-telegram-bot (or async Telegram API client), SQLAlchemy ORM, pydantic

## Multi-Dentist Support - ✅ FULLY OPERATIONAL

### Current Dentists in System
- **Hector** (ID: cb631d65-b84a-4b5b-9bbb-79e21eaa2b8a)
  - Calendar: `ae78cb2baac3e3318905a077b189140ef6226295e16f337fadb249caa483ea80@group.calendar.google.com`
  - Status: Active ✅

- **Fulano** (ID: 2a37ade0-aebe-466a-8b26-989107dd31a0)
  - Calendar: `763763f89e73f62085b6f2f9f0c6eebdd214fb2507dbaf88a5de70f32dd620c4@group.calendar.google.com`
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
