# API Contracts: Appointment Booking

**Date**: 2026-04-04  
**Feature**: [Appointment Booking with Google Calendar](../spec.md)  
**Type**: Telegram Webhook Integration (extends /webhook endpoint)

---

## Overview

The appointment booking feature extends the existing `/webhook` endpoint with a new state machine for appointment booking flow. The flow is:

1. User sends "1" (select "Solicitar turno" from menu)
2. System fetches available Google Calendar slots
3. System displays available slots to user
4. User selects a slot by number
5. System prompts for consultation reason
6. User provides reason
7. System books appointment and confirms

All communication is via Telegram messages (no new HTTP endpoints).

---

## Webhook Contract (POST /webhook)

**Base Contract**: Extends existing contract from Feature 001 (see `specs/001-webhook-menu/contracts/menu_routing.md`)

### New Conversation States

**Conversation State Transitions** (added to existing `ConversationStateEnum`):

```
AWAITING_MENU (existing)
├─ User selects "1" (Solicitar turno)
│  └─> AWAITING_SLOT_SELECTION (NEW)
│       ├─ System displays available slots
│       └─ User selects slot by number (e.g., "1", "2", "3")
│          └─> AWAITING_REASON_TEXT (NEW)
│              ├─ System prompts for consultation reason
│              └─ User provides reason text (1-150 chars)
│                 └─> APPOINTMENT_CONFIRMED (NEW)
│                     ├─ System confirms appointment
│                     └─> Return to AWAITING_MENU or COMPLETED
│
└─ User selects "2" (Hablar con secretaria)
   └─> [existing behavior from Feature 001]
```

### Message Flow Example

```
User:   "1"
System: "Disponibilidad de turnos:
         1. Lunes 08 de abril, 08:00-09:00
         2. Martes 09 de abril, 09:00-10:00
         3. Martes 09 de abril, 10:00-11:00
         Escoge el turno deseado (1-3):"

User:   "2"
System: "Entendido. Indícanos el motivo de tu consulta (máx 150 caracteres):"

User:   "Dolor de cabeza y mareos"
System: "✅ Tu turno ha sido confirmado:
         Martes 09 de abril, 09:00-10:00
         Motivo: Dolor de cabeza y mareos
         
         ¿Deseas volver al menú principal?"

User:   "sí"
System: [Display menu again - Feature 001]
```

---

## Telegram Message Schemas

### Outbound Messages (System → User)

#### Slot List Message

**Sent by**: `appointment_service.fetch_and_display_slots()`

**Format**:
```json
{
  "chat_id": 123456789,
  "text": "Disponibilidad de turnos:\n1. Lunes 08 de abril, 08:00-09:00\n2. Martes 09 de abril, 09:00-10:00\n3. Martes 09 de abril, 10:00-11:00\nEscoge el turno deseado (1-3):",
  "parse_mode": "HTML"
}
```

**Validation**:
- Each line includes: `{number}. {date_display}, {time_display}`
- Date format: Day name + date (e.g., "Lunes 08 de abril")
- Time format: HH:MM-HH:MM in clinic timezone (e.g., "08:00-09:00")
- Maximum 20 slots displayed (pagination if needed in future)
- Always includes closing instruction in Spanish

#### Reason Prompt Message

**Sent by**: `appointment_service.prompt_for_reason()`

**Format**:
```json
{
  "chat_id": 123456789,
  "text": "Entendido. Indícanos el motivo de tu consulta (máx 150 caracteres):",
  "parse_mode": "HTML"
}
```

#### Confirmation Message

**Sent by**: `appointment_service.confirm_appointment()`

**Format**:
```json
{
  "chat_id": 123456789,
  "text": "✅ Tu turno ha sido confirmado:\nMartes 09 de abril, 09:00-10:00\nMotivo: Dolor de cabeza y mareos\n\n¿Deseas volver al menú principal?",
  "parse_mode": "HTML"
}
```

**Validation**:
- Includes appointment confirmation emoji (✅)
- Shows date, time, and reason exactly as provided
- Offers menu return option

#### Error Messages

**No slots available**:
```
"No hay turnos disponibles en este momento. 
Contáctanos a través de la secretaria: /secretaria"
```

**Invalid slot selection**:
```
"Turno inválido. Elige un número de la lista (1-{max_slots})."
```

**Slot already booked (concurrent conflict)**:
```
"Lo sentimos, ese turno ya fue reservado. 
Elige otro:"
[Show updated slot list]
```

**Reason too long**:
```
"El motivo es muy largo (máx 150 caracteres). 
Intenta de nuevo:"
```

**Reason empty**:
```
"Por favor, indica un motivo para tu consulta."
```

**Google Calendar API error**:
```
"Sistema de turnos no disponible en este momento. 
Contacta a la secretaria."
```

### Inbound Messages (User → System)

#### Slot Selection

**Sent by**: User message after slot list

**Validation Rules**:
- Must be a single number: `^\d+$` regex
- Must be in range: `1 <= number <= len(available_slots)`
- Whitespace trimmed

**Example**:
```json
{
  "update_id": 987654321,
  "message": {
    "message_id": 1,
    "chat": {"id": 123456789, "type": "private"},
    "from": {"id": 123456789, "is_bot": false, "first_name": "Juan"},
    "text": "2",
    "date": 1680000000
  }
}
```

#### Reason Text

**Sent by**: User message after reason prompt

**Validation Rules**:
- Non-empty after stripping whitespace: `.strip() != ""`
- Maximum 150 characters: `len(text) <= 150`
- No validation on content (medical system responsibility)

**Example**:
```json
{
  "update_id": 987654322,
  "message": {
    "message_id": 2,
    "chat": {"id": 123456789, "type": "private"},
    "from": {"id": 123456789, "is_bot": false, "first_name": "Juan"},
    "text": "Dolor de cabeza y mareos",
    "date": 1680000001
  }
}
```

---

## Service Layer Contracts

### GoogleCalendarClient Interface

**Purpose**: Fetch available slots from Google Calendar API

**Methods**:

```python
class GoogleCalendarClient:
    """
    Wrapper around Google Calendar API.
    Authenticates with service account credentials.
    """
    
    async def get_available_slots(
        self,
        date_start: date,
        date_end: date,
        business_hours: tuple[time, time] = (time(8, 0), time(13, 0))
    ) -> list[AvailableSlot]:
        """
        Fetch available appointment slots from Google Calendar.
        
        Args:
            date_start: Start date for slot search
            date_end: End date for slot search  
            business_hours: Tuple of (start_time, end_time) in clinic timezone
        
        Returns:
            List of AvailableSlot objects with date, start_time, end_time
        
        Raises:
            GoogleCalendarAuthError: Invalid/expired credentials
            GoogleCalendarAPIError: Rate limit, quota, or transient API error
            GoogleCalendarTimeoutError: API response timeout (>10s)
        
        Contract:
            - Only returns Monday-Friday slots
            - Only returns slots within business_hours
            - Generates 1-hour increments
            - Returns slots in ascending chronological order
            - Excludes already-booked slots (queries local appointments table)
            - Caches results for 1 hour (optional, per research.md)
        """
        ...
    
    async def get_calendar_events(
        self,
        date_start: date,
        date_end: date
    ) -> list[CalendarEvent]:
        """
        Low-level: Fetch raw events from Google Calendar.
        Used internally by get_available_slots.
        
        Returns:
            List of CalendarEvent dicts with start, end, summary
        """
        ...
```

**Error Handling Contract**:

| Error | Status | User Message | Logging |
|-------|--------|--------------|---------|
| Invalid credentials (403) | FAIL | "Sistema no disponible, contacta a la secretaria" | ERROR: Log credentials check |
| Rate limit (429) | DEGRADE | Use cached slots or "Intenta en unos minutos" | WARN: Rate limit hit |
| Timeout (>10s) | RETRY | "Conectando..." | INFO: Retry attempt N/3 |
| Network error | RETRY | "Error de conexión" | WARN: Transient error |

---

### AppointmentService Interface

**Purpose**: Orchestrate appointment booking flow

**Methods**:

```python
class AppointmentService:
    """
    Business logic for appointment booking flow.
    Coordinates Google Calendar fetch, slot presentation, and booking.
    """
    
    async def fetch_and_display_slots(
        self,
        user_id: int,
        session: AsyncSession
    ) -> tuple[list[AvailableSlot], str]:
        """
        Fetch Google Calendar slots and format for Telegram.
        
        Args:
            user_id: Telegram user ID
            session: Database session
        
        Returns:
            (available_slots, formatted_message_text)
        
        Raises:
            NoSlotsAvailableError: Calendar has no available slots
            GoogleCalendarError: Calendar API error (delegated)
        
        Contract:
            - Returns up to 20 slots
            - Formats dates in Spanish day names
            - Formats times in clinic timezone (HH:MM format)
            - Includes instruction text in Spanish
        """
        ...
    
    async def validate_and_book_slot(
        self,
        user_id: int,
        slot_index: int,
        available_slots: list[AvailableSlot],
        reason: str,
        created_by_phone: str = None,
        session: AsyncSession = None
    ) -> Appointment:
        """
        Validate slot selection and reason, then book appointment.
        
        Args:
            user_id: Patient Telegram user ID
            slot_index: 1-based index into available_slots list
            available_slots: The slot list shown to user
            reason: Consultation reason (1-150 chars)
            created_by_phone: Optional staff phone number
            session: Database session
        
        Returns:
            Appointment object (saved to DB)
        
        Raises:
            InvalidSlotError: slot_index out of range
            SlotAlreadyBookedError: Concurrent booking (IntegrityError caught)
            InvalidReasonError: Reason too long or empty
            
        Contract:
            - Validates reason length (1-150 chars)
            - Validates slot_index in range [1, len(available_slots)]
            - Re-checks slot not booked (UNIQUE constraint safety)
            - On IntegrityError: Raises SlotAlreadyBookedError
            - Creates Appointment with status=PENDING
            - Logs to audit_log
            - Transaction atomic: booking fails entirely or succeeds
        """
        ...
    
    async def format_confirmation(
        self,
        appointment: Appointment
    ) -> str:
        """
        Format appointment confirmation message for Telegram.
        
        Returns:
            HTML-formatted message with date, time, reason
        """
        ...
```

---

### SlotGenerator Interface

**Purpose**: Generate available 1-hour slots from calendar events

**Methods**:

```python
class SlotGenerator:
    """
    Generate appointment slots from Google Calendar data.
    Excludes booked times, respects business hours.
    """
    
    @staticmethod
    def generate_available_slots(
        calendar_events: list[CalendarEvent],
        date_range: tuple[date, date],
        business_hours: tuple[time, time] = (time(8, 0), time(13, 0)),
        slot_duration_minutes: int = 60
    ) -> list[AvailableSlot]:
        """
        Generate slots from calendar events.
        
        Args:
            calendar_events: List of booked events from Google Calendar
            date_range: (start_date, end_date) to generate slots for
            business_hours: (start_time, end_time) in clinic timezone
            slot_duration_minutes: Duration of each slot (default 60)
        
        Returns:
            List of AvailableSlot objects
        
        Contract:
            - Only generates Mon-Fri slots
            - Only generates within business_hours
            - Generates 1-hour increments (60 min)
            - Excludes slots that overlap with calendar_events
            - Excludes past times (datetime now)
            - Returns slots sorted by date+time ascending
            - Handles timezone correctly (all times in UTC)
        """
        ...
```

---

## Conversation State Machine Contract

### StateEnum (extends Feature 001)

```python
class ConversationStateEnum(str, Enum):
    # Existing from Feature 001
    AWAITING_MENU = "AWAITING_MENU"
    AWAITING_SELECTION = "AWAITING_SELECTION"
    SECRETARY_SELECTED = "SECRETARY_SELECTED"
    COMPLETED = "COMPLETED"
    INACTIVE = "INACTIVE"
    
    # New for Feature 002
    AWAITING_SLOT_SELECTION = "AWAITING_SLOT_SELECTION"
    AWAITING_REASON_TEXT = "AWAITING_REASON_TEXT"
    APPOINTMENT_CONFIRMED = "APPOINTMENT_CONFIRMED"
```

### State Transition Table

| From State | Trigger | Condition | To State | Action |
|------------|---------|-----------|----------|--------|
| AWAITING_MENU | Message="1" | Menu selection recognized | AWAITING_SLOT_SELECTION | Fetch slots & display |
| AWAITING_SLOT_SELECTION | Message=number | 1 ≤ number ≤ slot_count | AWAITING_REASON_TEXT | Prompt for reason |
| AWAITING_SLOT_SELECTION | Message=other | Invalid selection | AWAITING_SLOT_SELECTION | Show error, redisplay slots |
| AWAITING_REASON_TEXT | Message=text | 1 ≤ len(text) ≤ 150 | APPOINTMENT_CONFIRMED | Book appointment |
| AWAITING_REASON_TEXT | Message=empty/long | Invalid reason | AWAITING_REASON_TEXT | Show error, reprompt |
| APPOINTMENT_CONFIRMED | Message=any | - | AWAITING_MENU | Reset to menu |
| Any state | Timeout >5 min | User inactive | INACTIVE | End conversation |

---

## Database Contract

### Unique Constraint (Critical for double-booking prevention)

```sql
ALTER TABLE appointments
ADD CONSTRAINT uq_appointment_slot
UNIQUE (appointment_date, start_time);
```

**Contract**:
- Enforced at transaction level (PostgreSQL ACID)
- If concurrent INSERT violates constraint → transaction fails with `UniqueViolationError`
- Application must catch and retry with updated slot list

### Referential Integrity

```sql
ALTER TABLE appointments
ADD CONSTRAINT fk_patient_user_id
FOREIGN KEY (patient_user_id) REFERENCES telegram_users(id)
ON DELETE CASCADE;

ALTER TABLE appointments
ADD CONSTRAINT fk_created_by_user_id
FOREIGN KEY (created_by_user_id) REFERENCES telegram_users(id)
ON DELETE SET NULL;
```

---

## Error Codes & Handling

### Application Error Codes

| Code | Exception | HTTP (if applicable) | Telegram Response | Action |
|------|-----------|-------------------|-------------------|--------|
| SLOT_001 | InvalidSlotError | 400 | "Turno inválido" | Re-prompt |
| SLOT_002 | SlotAlreadyBookedError | 409 | "Turno ya reservado" | Fetch new slots, re-prompt |
| SLOT_003 | NoSlotsAvailableError | 410 | "No hay turnos disponibles" | Offer secretary contact |
| REASON_001 | InvalidReasonError | 400 | "Motivo inválido (longitud)" | Re-prompt |
| REASON_002 | ReasonEmptyError | 400 | "Motivo no puede estar vacío" | Re-prompt |
| CALENDAR_001 | GoogleCalendarAuthError | 500 | "Sistema no disponible" | Log error, offer secretary |
| CALENDAR_002 | GoogleCalendarAPIError | 503 | "Error de calendario" | Retry with backoff |
| CALENDAR_003 | GoogleCalendarTimeoutError | 504 | "Conectando..." | Retry up to 3 times |
| DB_001 | DatabaseError | 500 | "Error de base de datos" | Log error, offer secretary |
| VALIDATION_001 | ConversationStateError | 400 | "Estado inválido" | Reset conversation |

---

## Testing Contract

### Unit Test Requirements

1. **SlotGenerator**: Generate correct slots for calendar events
2. **AppointmentService**: Validate reasons, prevent invalid bookings
3. **GoogleCalendarClient**: Mock API responses, error handling

### Integration Test Requirements

1. **Full booking flow**: User → Menu → Slots → Selection → Reason → Confirmation
2. **Concurrent booking**: Two users select same slot simultaneously (second gets error)
3. **Error recovery**: API timeout, then fallback to cached slots
4. **Timezone consistency**: Slots displayed in clinic TZ, stored in UTC

### Test Scenarios

```gherkin
Scenario: User successfully books appointment
  Given user selects "Solicitar turno"
  When system displays available slots
  And user selects slot "1"
  And user provides reason "Consulta general"
  Then appointment is created with status PENDING
  And confirmation message shown to user

Scenario: Concurrent booking prevention
  Given 2 users selecting same slot
  When both attempt booking simultaneously
  Then first booking succeeds
  And second receives "turno ya reservado" error
  And second shown updated slot list

Scenario: Calendar API timeout
  Given Google Calendar API is slow (>10s)
  When system fetches slots
  Then after timeout, uses cached slots
  And displays "Disponibilidad no actualizada"
```

---

## Summary

- **Stateless Design**: All state in database (ConversationState), no session memory
- **Concurrent Safe**: UNIQUE constraint + optimistic retry
- **Error Resilient**: Graceful fallbacks, user-friendly Spanish messages
- **Audit Trail**: All appointments logged to audit_log
- **Extensible**: Contracts support future features (doctor confirmation, multi-calendar)

