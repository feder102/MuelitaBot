# Quickstart: Appointment Booking Integration

**Date**: 2026-04-04  
**Feature**: [Appointment Booking with Google Calendar](spec.md)  
**Duration**: ~30 minutes to set up locally

---

## Prerequisites

- Feature 001 (webhook menu) implemented and running
- Python 3.11+ with project dependencies installed
- PostgreSQL database running (from docker-compose)
- Google account with Google Calendar enabled
- Terminal access to run commands

---

## Step 1: Set Up Google Calendar API

### 1.1 Create Google Cloud Project

```bash
# 1. Go to https://console.cloud.google.com/
# 2. Create a new project named "TurnoHector"
# 3. Enable Google Calendar API:
#    - Search "Google Calendar API" in search bar
#    - Click "Enable"
```

### 1.2 Create Service Account

```bash
# In Google Cloud Console:
# 1. Go to "Service Accounts" (APIs & Services > Credentials)
# 2. Click "Create Service Account"
# 3. Name: "turno-hector-service"
# 4. Click "Create and Continue"
# 5. Click "Create Key" → Select "JSON"
# 6. Save the JSON file as `google-creds.json` in your project root
```

### 1.3 Share Calendar with Service Account

```bash
# 1. In Google Cloud Console, copy the service account email:
#    Example: turno-hector-service@turnohector-12345.iam.gserviceaccount.com
#
# 2. In Google Calendar (calendar.google.com):
#    - Open "Settings" (gear icon)
#    - Select the calendar (e.g., "Medical Appointments")
#    - Go to "Share with specific people or groups"
#    - Add the service account email
#    - Grant "Editor" access (can read & modify events)
#
# 3. Create test events on calendar:
#    - Monday 08:00-09:00
#    - Monday 09:00-10:00
#    - Tuesday 10:00-11:00
#    (These should appear as unavailable when you query the API)
```

### 1.4 Get Calendar ID

```bash
# In Google Calendar Settings:
# 1. Select the calendar
# 2. Scroll to "Calendar ID" (e.g., "abc123@group.calendar.google.com")
# 3. Copy this value
```

---

## Step 2: Configure Environment Variables

### 2.1 Update `.env` file

```bash
# Add to existing .env:

# Google Calendar Configuration
GOOGLE_CALENDAR_CREDENTIALS_B64=$(cat google-creds.json | base64 -w 0)
GOOGLE_CALENDAR_ID=abc123@group.calendar.google.com
CLINIC_TIMEZONE=America/Argentina/Buenos_Aires

# Appointment Configuration
APPOINTMENT_SLOTS_START_TIME=08:00
APPOINTMENT_SLOTS_END_TIME=13:00
APPOINTMENT_REASON_MAX_LENGTH=150
```

**Note**: Replace `google-creds.json` content and calendar ID with your actual values.

### 2.2 Add to `.env.example` for future developers

```bash
cat >> .env.example << 'EOF'

# Google Calendar (Feature 002)
GOOGLE_CALENDAR_CREDENTIALS_B64=<base64-encoded service account JSON>
GOOGLE_CALENDAR_ID=<medical-center-calendar@group.calendar.google.com>
CLINIC_TIMEZONE=America/Argentina/Buenos_Aires
APPOINTMENT_SLOTS_START_TIME=08:00
APPOINTMENT_SLOTS_END_TIME=13:00
APPOINTMENT_REASON_MAX_LENGTH=150
EOF
```

---

## Step 3: Update Configuration Code

### 3.1 Extend `src/config.py`

```python
import base64
import json
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ... existing settings ...
    
    # Google Calendar Configuration
    google_calendar_credentials_b64: str = ""
    google_calendar_id: str = ""
    clinic_timezone: str = "America/Argentina/Buenos_Aires"
    
    # Appointment Configuration
    appointment_slots_start_time: str = "08:00"
    appointment_slots_end_time: str = "13:00"
    appointment_reason_max_length: int = 150
    
    @property
    def google_calendar_credentials(self) -> dict:
        """Decode base64-encoded service account credentials."""
        if not self.google_calendar_credentials_b64:
            raise ValueError("GOOGLE_CALENDAR_CREDENTIALS_B64 not set")
        creds_json = base64.b64decode(self.google_calendar_credentials_b64).decode()
        return json.loads(creds_json)
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

---

## Step 4: Run Database Migration

```bash
# From project root:
alembic upgrade head

# Output should include:
# [alembic.migration] Running upgrade 001 -> 002_add_appointments
# [alembic.runtime.sqlalchemy] CREATE TABLE appointments ...
```

---

## Step 5: Test Google Calendar Connection

### 5.1 Create a test script

```python
# test_google_calendar_local.py
import asyncio
from datetime import date, time, timedelta
from src.config import settings
from src.services.google_calendar_client import GoogleCalendarClient

async def test_calendar():
    client = GoogleCalendarClient(
        credentials_dict=settings.google_calendar_credentials,
        calendar_id=settings.google_calendar_id,
        clinic_timezone=settings.clinic_timezone
    )
    
    tomorrow = date.today() + timedelta(days=1)
    next_week = tomorrow + timedelta(days=7)
    
    print("Fetching calendar events...")
    try:
        slots = await client.get_available_slots(
            date_start=tomorrow,
            date_end=next_week,
            business_hours=(time(8, 0), time(13, 0))
        )
        
        print(f"\n✅ Found {len(slots)} available slots:")
        for i, slot in enumerate(slots, 1):
            print(f"   {i}. {slot.date_display} {slot.time_display}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_calendar())
```

### 5.2 Run the test

```bash
python test_google_calendar_local.py

# Expected output:
# ✅ Found 4 available slots:
#    1. Lunes 08 de abril, 08:00-09:00
#    2. Martes 09 de abril, 09:00-10:00
#    3. Miércoles 10 de abril, 10:00-11:00
#    4. Jueves 11 de abril, 08:00-09:00
```

**Troubleshooting**:
- **403 Forbidden**: Calendar not shared with service account email
- **Invalid credentials**: Base64 decoding failed, check `.env`
- **No slots**: All times are booked, add more events to Google Calendar

---

## Step 6: Test Full Appointment Booking Flow

### 6.1 Start the application

```bash
# Terminal 1: Start Docker services
docker-compose up -d

# Terminal 2: Start FastAPI server
python -m uvicorn src.main:app --reload --port 8000
```

### 6.2 Send test webhook request

```bash
# Use curl or Postman to simulate Telegram webhook:

# First, send "1" (Solicitar turno)
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Bot-API-Secret-SHA256: $(echo -n '{your payload}' | openssl dgst -sha256 -mac HMAC -macopt key:$TELEGRAM_BOT_WEBHOOK_SECRET -binary | base64)" \
  -d '{
    "update_id": 1,
    "message": {
      "message_id": 1,
      "chat": {"id": 123456789, "type": "private"},
      "from": {"id": 123456789, "is_bot": false, "first_name": "Juan"},
      "text": "1",
      "date": 1680000000
    }
  }'

# Expected response: Telegram sendMessage with available slots
```

### 6.3 Test via Telegram Bot (recommended)

```bash
# 1. Get your Telegram user ID:
#    Send "/start" to @userinfobot
#    Note the returned user ID
#
# 2. Set up webhook forwarding (ngrok, tunnelmole, or port-forward)
#    ngrok http 8000
#
# 3. Configure webhook URL in Telegram Bot API:
#    curl -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" \
#      -F url="https://your-ngrok-url.ngrok.io/webhook" \
#      -F secret_token="$TELEGRAM_BOT_WEBHOOK_SECRET"
#
# 4. Send messages to your bot:
#    - Send "1" → See available slots
#    - Send "1" (slot number) → See reason prompt
#    - Send "Dolor de cabeza" → See confirmation
```

---

## Step 7: Database Inspection

### 7.1 Check appointments table

```bash
# Connect to PostgreSQL
docker exec -it turno_hector_db psql -U postgres -d turno_hector

# Query appointments
SELECT id, patient_user_id, appointment_date, start_time, reason, status
FROM appointments
ORDER BY created_at DESC;

# Query cached slots (if implemented)
SELECT slot_date, start_time, is_available, expires_at
FROM cached_calendar_slots
ORDER BY slot_date, start_time;

# Exit
\q
```

---

## Step 8: Run Integration Tests

```bash
# Test appointment booking flow
pytest tests/integration/test_appointment_booking_flow.py -v

# Test double-booking prevention
pytest tests/integration/test_double_booking_prevention.py -v

# Test Google Calendar client
pytest tests/unit/test_google_calendar_client.py -v

# Full test suite with coverage
pytest tests/ --cov=src --cov-report=html
# Open htmlcov/index.html to view coverage
```

---

## Development Workflow

### Adding a Test Google Calendar Event

```python
# In Google Calendar API (via service account):
# Create event for testing

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

creds = Credentials.from_service_account_info(
    settings.google_calendar_credentials
)
service = build('calendar', 'v3', credentials=creds)

event = {
    'summary': 'Test Event',
    'start': {'dateTime': '2026-04-08T10:00:00', 'timeZone': 'America/Argentina/Buenos_Aires'},
    'end': {'dateTime': '2026-04-08T11:00:00', 'timeZone': 'America/Argentina/Buenos_Aires'},
}
service.events().insert(calendarId=settings.google_calendar_id, body=event).execute()
```

### Clearing Test Data

```bash
# Delete all test appointments
DELETE FROM appointments WHERE reason LIKE 'Test%';

# Clear cached slots
DELETE FROM cached_calendar_slots;

# Reset user conversation state
UPDATE conversation_state SET state='AWAITING_MENU' WHERE user_id = YOUR_USER_ID;
```

---

## Common Issues & Solutions

### Issue: "Google Calendar API is not enabled"
**Solution**: Go to Google Cloud Console > APIs & Services > Enable "Google Calendar API"

### Issue: "403 Forbidden" when querying calendar
**Solution**: Ensure service account email is added as "Editor" to the calendar in Google Calendar Settings

### Issue: Slots not appearing or all showing as booked
**Solution**: 
- Check calendar ID is correct in `.env`
- Create some test events in Google Calendar for future dates
- Verify `CLINIC_TIMEZONE` matches your calendar timezone

### Issue: "UNIQUE constraint violation" when booking
**Solution**: This is expected! Means concurrent booking detected. User should see error and can select another slot.

### Issue: "Slots show UTC time instead of clinic timezone"
**Solution**: Check `CLINIC_TIMEZONE` environment variable and ensure `pytz` is installed

---

## Verification Checklist

- [ ] Google Cloud Project created and Calendar API enabled
- [ ] Service account created and credentials saved as JSON
- [ ] Calendar shared with service account email
- [ ] `.env` file updated with GOOGLE_CALENDAR_* variables
- [ ] Database migration applied (`alembic upgrade head`)
- [ ] Test script `test_google_calendar_local.py` runs successfully
- [ ] At least one appointment booked via test request
- [ ] Appointment appears in `appointments` table
- [ ] Integration tests pass (pytest)
- [ ] No errors in application logs

---

## Next Steps

1. Implement `GoogleCalendarClient` in `src/services/google_calendar_client.py`
2. Implement `AppointmentService` in `src/services/appointment_service.py`
3. Implement `SlotGenerator` in `src/services/slot_generator.py`
4. Extend `webhook.py` with appointment booking state handlers
5. Write unit and integration tests
6. Performance test with concurrent bookings

---

## Resources

- [Google Calendar API Documentation](https://developers.google.com/calendar/api/guides/overview)
- [Service Accounts Setup](https://developers.google.com/identity/protocols/oauth2/service-account)
- [Google API Python Client](https://github.com/googleapis/google-api-python-client)
- [Telegram Bot API Webhook Documentation](https://core.telegram.org/bots/api#setwebhook)
- [PostgreSQL UNIQUE Constraints](https://www.postgresql.org/docs/15/ddl-constraints.html)

