# turnoHector - Telegram Webhook Menu Backend

A FastAPI-based backend for managing Telegram bot webhooks and interactive menu routing. Designed for medical appointment management with security-first principles.

## Features

- **Telegram Webhook Integration**: Secure HMAC-SHA256 signature validation
- **Interactive Menu System**: Display numbered menu options to users
- **State Management**: Track user conversation state across messages
- **Audit Logging**: Immutable audit trail for compliance and debugging
- **Async Support**: Built on FastAPI with SQLAlchemy async for high concurrency
- **Medical Data Protection**: PHI encryption and security standards

## Project Structure

```
src/
├── main.py                      # FastAPI application entry point
├── config.py                    # Configuration management
├── db.py                        # Database setup
├── models/                      # ORM models
│   ├── telegram_user.py
│   ├── conversation_state.py
│   └── audit_log.py
├── schemas/                     # Pydantic validation models
│   └── telegram_webhook.py
├── api/                         # API endpoints
│   └── webhook.py
├── services/                    # Business logic
│   ├── message_parser.py
│   ├── conversation_manager.py
│   ├── menu_router.py
│   └── webhook_handler.py
└── utils/                       # Utilities
    ├── signature_validator.py
    ├── telegram_client.py
    └── logger.py

tests/
├── unit/                        # Unit tests
├── integration/                 # Integration tests
├── contract/                    # API contract tests
└── load/                        # Load/performance tests

migrations/                      # Database migrations
└── versions/
    └── 001_initial_schema.py
```

## Quick Start

### 1. Setup Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Edit .env and add:
# - TELEGRAM_BOT_TOKEN (from BotFather)
# - TELEGRAM_BOT_WEBHOOK_SECRET (generate random 32+ char string)
```

### 2. Start PostgreSQL

```bash
docker-compose up -d postgres
# Wait for healthy status:
docker-compose ps
```

### 3. Run Database Migrations

```bash
# Using Alembic (requires installation)
alembic upgrade head

# Or in development: FastAPI auto-creates tables on startup
```

### 4. Start API Server

```bash
# Development with auto-reload
python3 src/main.py

# Or with uvicorn directly:
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# View API docs
# http://localhost:8000/docs  (Swagger UI)
# http://localhost:8000/redoc (ReDoc)
```

### 4a. Viewing Logs

The application outputs detailed logs to help track the booking flow:

```bash
# All logs go to stdout automatically
# Run the app and watch for these key logs:

# When user selects appointment (sends "1"):
📋 Initializing AppointmentRouter...
🔍 fetch_and_show_slots() called
📅 Fetching slots from YYYY-MM-DD to YYYY-MM-DD
✅ Got 25 slots from service

# When user selects a slot (sends "1"):
📊 AWAITING_SLOT_SELECTION: user_input=1, available_slots=25
✅ Slot validation result: new_state=AWAITING_REASON_TEXT

# When user enters consultation reason:
📋 AWAITING_REASON_TEXT: Processing user reason input
✓ Found selected_slot in context_data
🔍 Validating reason: 'Consulta de rutina'
📝 Booking appointment: patient=<uuid>, slot=YYYY-MM-DD HH:MM:SS-HH:MM:SS

# When Google Calendar event is created:
✓ Appointment saved to DB
🔗 About to create Google Calendar event...
📅 Creating Google Calendar event: date=YYYY-MM-DD
🔧 Building event: summary='Cita: Consulta de rutina'
🚀 Sending event creation request to Google Calendar API...
✅ Google Calendar event created successfully! Event ID: <event_id>
✅ Appointment booked successfully!
```

**To see logs with timestamps and levels**:
```bash
# The default logging shows JSON format. You can tail the output:
python3 src/main.py 2>&1 | tee logs.txt

# Or filter for specific keywords:
python3 src/main.py 2>&1 | grep "✅\|❌\|📅\|📋"
```

**Log Levels** (set in `.env`):
- `LOG_LEVEL=DEBUG` - All logs including SQL queries
- `LOG_LEVEL=INFO` - Normal operation (default)
- `LOG_LEVEL=WARNING` - Only warnings and errors
- `LOG_LEVEL=ERROR` - Only errors

### 6. Setup Telegram Webhook

```bash
# Get your public URL (using ngrok for local development):
ngrok http 8000  # Get forward URL like https://xxxx-xx-xxx-xxx.ngrok.io

# Set webhook with your bot
python3 << 'EOF'
import requests

BOT_TOKEN = "YOUR_TOKEN_HERE"
WEBHOOK_URL = "https://your-ngrok-url/webhook"
SECRET = "your-secret-from-.env"

url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
data = {
    "url": WEBHOOK_URL,
    "secret_token": SECRET,
    "allowed_updates": ["message"]
}
response = requests.post(url, json=data)
print(response.json())  # Should show "ok": true
EOF
```

### 7. Test with Telegram Bot

1. Find your bot: `@yourbot_username`
2. Send any message → Bot responds with menu
3. Send "1" → Appointment flow
4. Send "2" → Secretary contact

## API Endpoints

### POST /webhook
Receive Telegram webhook updates. Requires valid HMAC-SHA256 signature.

**Request**:
```json
{
  "update_id": 123,
  "message": {
    "message_id": 1,
    "date": 1234567890,
    "chat": {
      "id": 12345,
      "type": "private",
      "first_name": "Juan"
    },
    "text": "Hola"
  }
}
```

**Response**:
```json
{
  "ok": true
}
```

### GET /health
Health check endpoint.

```json
{
  "status": "healthy"
}
```

### GET /
API information and links.

## Database Schema

### telegram_users
- id (UUID): Primary key
- telegram_user_id (BIGINT): Unique Telegram ID
- first_name, last_name, username: User info
- is_active: Soft delete flag
- created_at, updated_at: Timestamps

### conversation_state
- user_id (UUID FK): Foreign key to telegram_users
- current_state (ENUM): AWAITING_MENU, AWAITING_SELECTION, APPOINTMENT_SELECTED, SECRETARY_SELECTED, COMPLETED, INACTIVE
- last_interaction: Last message timestamp
- menu_display_count: How many times menu shown
- metadata: JSONB for extensibility

### audit_log
- id (UUID): Primary key
- user_id (UUID FK): Foreign key (nullable for failed auth)
- action (VARCHAR): WEBHOOK_RECEIVED, MESSAGE_PARSED, MENU_DISPLAYED, etc.
- status (ENUM): SUCCESS, VALIDATION_FAILED, ERROR
- message_text, response_text: Audit trail
- error_detail: Error details
- ip_address: Source IP
- created_at: Immutable timestamp

## Environment Variables

See `.env.example` for complete list:

```
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_BOT_WEBHOOK_SECRET=your_secret
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/dbname
API_PORT=8000
LOG_LEVEL=INFO
API_ENV=development
```

## Development

### Code Formatting & Linting

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint
flake8 src/ tests/
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=src --cov-report=html

# Specific test file
pytest tests/unit/test_signature_validator.py -v

# Live debugging
pytest tests/ -v -s
```

### Load Testing

```bash
# Install locust
pip install locust

# Run load tests
locust -f tests/load/load_test.py --host http://localhost:8000
```

## Security

- **Webhook Signature Validation**: HMAC-SHA256 per Telegram spec
- **No Hardcoded Secrets**: All credentials from environment
- **Input Validation**: Pydantic schemas validate all inputs
- **Audit Logging**: All actions logged for compliance
- **Database Encryption**: TLS for connections (production)
- **Error Handling**: Server logs details, clients get generic messages

## Production Deployment

### Docker

```bash
# Build image
docker build -t turnohector:latest .

# Run with compose
docker-compose up -d

# Run migrations
docker-compose exec api alembic upgrade head
```

### Environment Setup

- Use managed PostgreSQL (AWS RDS, Azure, GCP Cloud SQL)
- Store secrets in secrets manager (AWS Secrets Manager, etc.)
- Use HTTPS with valid certificate
- Enable database backups
- Setup monitoring and alerting

### Scaling

- Horizontal: Stateless backend scales easily
- Database: Connection pooling configured (max 20)
- Async: Handles 100+ concurrent requests
- Caching: Optional Redis for state (future)

## Configuration

### Application Settings

Settings are loaded from `.env` file via Pydantic:

```python
from src.config import settings

settings.telegram_bot_token      # Bot token
settings.database_url            # Database connection
settings.log_level               # Logging level
settings.is_development          # Environment check
```

### Logging

Structured JSON logging to stdout:

```json
{
  "timestamp": "2026-04-04T10:30:00.000Z",
  "level": "INFO",
  "message": "Webhook processed successfully",
  "module": "webhook_handler",
  "function": "handle_webhook",
  "line": 42
}
```

## Troubleshooting

### Bot Not Responding

1. Check bot token is correct: `curl https://api.telegram.org/bot<token>/getMe`
2. Verify webhook is set: `curl https://api.telegram.org/bot<token>/getWebhookInfo`
3. Check logs: `docker-compose logs api`
4. Verify signature validation: Enable debug logging

### Database Connection Issues

1. Verify PostgreSQL is running: `docker-compose ps`
2. Check connection string in `.env`
3. Test connection: `psql -h localhost -U postgres`
4. Check logs: `docker-compose logs postgres`

### Signature Validation Errors

1. Verify `TELEGRAM_BOT_WEBHOOK_SECRET` matches in setWebhook call
2. Ensure raw request body is used for validation (not parsed JSON)
3. Check ngrok/tunnel headers aren't modifying signature

## Managing Dentists (Multi-Dentist Support) ✅ ACTIVE

The system supports multiple dentists, each with their own Google Calendar for appointment booking.

### How Calendar IDs Work

**Important:** When you add a dentist with their calendar ID, that ID is stored in the database and used automatically:

```
Database (dentists table)
    ├── Hector → <hector_calendar_id@group.calendar.google.com>
    └── Fulano → <fulano_calendar_id@group.calendar.google.com>
            ↓
When booking appointment:
    └─→ Retrieved from DB → Passed to Google Calendar API
            ↓
Event created in THAT DENTIST'S calendar (NOT the .env calendar)
```

The `.env` `GOOGLE_CALENDAR_ID` is only used as a fallback. The system automatically retrieves each dentist's calendar ID from the database.

### ⚡ Quick Command to Add a Dentist

```bash
python scripts/seed_dentists.py "Doctor Name" "calendar_id@clinic.calendar.google.com"
```

#### Examples:

```bash
# Add Hector
python3 scripts/seed_dentists.py "Hector" "hector@clinic.calendar.google.com"

# Add Fulano
python3 scripts/seed_dentists.py "Fulano" "fulano@clinic.calendar.google.com"

# Add Dr. García
python3 scripts/seed_dentists.py "Dr. García" "garcia@clinic.calendar.google.com"
```

**Output:**
```
➕ Adding dentist: Hector
✅ Created dentist: Hector (ID: <generated_uuid>)
✅ Dentist seeded successfully
```

**Current Dentists in System:**
- ✅ **Hector** - `<hector_calendar_id@group.calendar.google.com>`
- ✅ **Fulano** - `<fulano_calendar_id@group.calendar.google.com>`

### What Happens After Adding a Doctor

✅ **Immediately available** in the appointment selection menu  
✅ **Calendar is linked** to their Google Calendar  
✅ **No code changes** required - fully database-driven  
✅ **Appears in bot menu** on next user interaction

### 📂 Alternative: Bulk Import from JSON

For adding multiple doctors at once:

```bash
# Create dentists.json
python scripts/seed_dentists.py --file dentists.json
```

**dentists.json format:**
```json
[
    {
        "name": "Hector",
        "calendar_id": "hector@clinic.calendar.google.com",
        "active_status": true
    },
    {
        "name": "Fulano",
        "calendar_id": "fulano@clinic.calendar.google.com",
        "active_status": true
    }
]
```

See `scripts/dentists.json.example` for template.

### ✅ Test Multi-Dentist Flow

Verify that the multi-dentist booking system is working correctly:

```bash
python3 scripts/test_multi_dentist_flow.py
```

**What it checks:**
- ✅ All active dentists are retrievable from database
- ✅ Appointment slots are fetched from each dentist's calendar
- ✅ Calendar IDs match between database and Google Calendar API
- ✅ Appointment model correctly links to dentist
- ✅ Multi-dentist support is enabled

**Expected output:**
```
🦷 MULTI-DENTIST APPOINTMENT BOOKING FLOW TEST
✅ Found 2 active dentist(s)
   1. Hector → <hector_calendar_id@group.calendar.google.com>
   2. Fulano → <fulano_calendar_id@group.calendar.google.com>
✅ Retrieved 30 slot(s) for Hector
✅ Retrieved 30 slot(s) for Fulano
✅ Hector's calendar ID: <hector_calendar_id@group.calendar.google.com> (Matches stored value)
✅ Fulano's calendar ID: <fulano_calendar_id@group.calendar.google.com> (Matches stored value)
✨ The system is ready to handle multiple dentists!
```

### 📋 View All Dentists

```bash
# Quick Python script to list all doctors:
python3 << 'EOF'
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.config import settings

async def list_dentists():
    engine = create_async_engine(settings.database_url)
    async_session = async_sessionmaker(engine, class_=AsyncSession)
    async with async_session() as session:
        result = await session.execute(text(
            "SELECT name, calendar_id, active_status FROM dentists ORDER BY name"
        ))
        print("\n📋 Doctors:\n")
        for name, cal, active in result:
            status = "🟢 ACTIVE" if active else "🔴 INACTIVE"
            print(f"  {name:20} → {cal:45} {status}")
    await engine.dispose()

asyncio.run(list_dentists())
EOF
```

### 🔧 Deactivate a Doctor

The doctor will no longer appear in the booking menu:

```bash
python3 << 'EOF'
import asyncio
from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.config import settings

async def deactivate(name):
    engine = create_async_engine(settings.database_url)
    async_session = async_sessionmaker(engine, class_=AsyncSession)
    async with async_session() as session:
        await session.execute(
            update("dentists").where(text(f"name = '{name}'")).values(active_status=False)
        )
        await session.commit()
        print(f"✅ Deactivated: {name}")
    await engine.dispose()

asyncio.run(deactivate("Hector"))
EOF
```

### 🔄 Update a Doctor's Calendar

If the doctor's Google Calendar changes:

```bash
python3 << 'EOF'
import asyncio
from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.config import settings

async def update_calendar(name, new_cal):
    engine = create_async_engine(settings.database_url)
    async_session = async_sessionmaker(engine, class_=AsyncSession)
    async with async_session() as session:
        await session.execute(
            update("dentists").where(text(f"name = '{name}'")).values(calendar_id=new_cal)
        )
        await session.commit()
        print(f"✅ Updated {name} → {new_cal}")
    await engine.dispose()

asyncio.run(update_calendar("Hector", "hector.new@clinic.calendar.google.com"))
EOF
```

### 👥 User Experience

**Single Dentist Clinic:**
```
User: 1 (Solicitar turno)
Bot: [Auto-selects doctor]
     [Shows available slots immediately]
```

**Multi-Dentist Clinic:**
```
User: 1 (Solicitar turno)
Bot: ¿A qué odontólogo deseas pedir turno?
     1. Hector
     2. Fulano
     3. Dr. García

User: 2
Bot: [Shows available slots for Fulano]
```

### 📊 Database Schema

```sql
-- Dentist table (NEW)
CREATE TABLE dentists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    calendar_id VARCHAR(255) NOT NULL UNIQUE,
    active_status BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Appointments table (EXTENDED)
ALTER TABLE appointments ADD COLUMN dentist_id UUID FOREIGN KEY REFERENCES dentists(id);
```

## Contributing

- Follow PEP 8 style guide
- Write tests for new features
- Ensure code coverage >80%
- Update documentation
- Commit messages: `type: description` format

## License

Proprietary - Fede Castiglione

## Support

For issues or questions, check:
- `/specs/001-webhook-menu/` for detailed specification
- `docs/` for additional documentation
- GitHub Issues for bug reports
