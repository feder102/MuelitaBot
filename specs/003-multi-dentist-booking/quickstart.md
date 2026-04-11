# Implementation Quickstart: Multi-Dentist Appointment Booking

**Feature**: 003-multi-dentist-booking | **Date**: 2026-04-05

## Implementation Overview

This feature extends the existing appointment booking system to support multiple dentists. The implementation follows the existing code patterns and maintains backward compatibility.

---

## Key Implementation Areas

### 1. Database Schema Changes

**File**: `migrations/versions/[new_migration].py` (Alembic)

**What to Add**:
- Create `dentists` table with `id`, `name`, `calendar_id`, `active_status`, timestamps
- Add `dentist_id` column to `appointments` table (FK to dentists)
- Update unique constraint on appointments to include `dentist_id`
- Create indexes on `dentist.active_status` and `appointment.dentist_id`

**Follow Existing Pattern**: See `migrations/versions/` for appointment table migration (Feature 002)

---

### 2. New ORM Model: Dentist

**File**: `src/models/dentist.py` (NEW)

**Template**:
```python
from uuid import uuid4
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.db import Base

class Dentist(Base):
    __tablename__ = "dentists"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(100), nullable=False, unique=True, index=True)
    calendar_id = Column(String(255), nullable=False, unique=True)
    active_status = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    appointments = relationship("Appointment", back_populates="dentist")
    
    def __repr__(self) -> str:
        return f"<Dentist(id={self.id}, name={self.name})>"
```

**Validation**: Follow constraints in [data-model.md](data-model.md)

---

### 3. Update Appointment Model

**File**: `src/models/appointment.py` (EXTEND)

**Changes**:
```python
# Add import
from sqlalchemy import ForeignKey

# In Appointment class, add:
dentist_id = Column(
    UUID(as_uuid=True),
    ForeignKey("dentists.id", ondelete="RESTRICT"),
    nullable=True,  # Nullable during transition, becomes NOT NULL after migration + app update
    index=True,
)

# Update relationship
dentist = relationship("Dentist", back_populates="appointments")

# Update __table_args__ constraint from:
#   UniqueConstraint("appointment_date", "start_time", name="uq_appointment_slot")
# To:
#   UniqueConstraint("dentist_id", "appointment_date", "start_time", name="uq_appointment_slot"),
```

---

### 4. New Service: DentistService

**File**: `src/services/dentist_service.py` (NEW)

**Methods to Implement**:
```python
class DentistService:
    """Manage dentist configuration and retrieval."""
    
    async def get_active_dentists(
        self, session: AsyncSession
    ) -> List[Dentist]:
        """Get all active dentists for booking menu."""
        # Query: SELECT * FROM dentists WHERE active_status = TRUE ORDER BY name
    
    async def get_dentist_by_id(
        self, session: AsyncSession, dentist_id: UUID
    ) -> Optional[Dentist]:
        """Get specific dentist (with validation)."""
        # Query: SELECT * FROM dentists WHERE id = ? AND active_status = TRUE
    
    async def get_dentist_calendar_id(
        self, session: AsyncSession, dentist_id: UUID
    ) -> str:
        """Get Google Calendar ID for dentist (reuse in GoogleCalendarClient)."""
        # Look up dentist, return calendar_id or raise DentistNotFoundError
```

**Error Handling**:
- `DentistNotFoundError`: When dentist_id doesn't exist or inactive
- `DentistInactiveError`: When dentist is marked inactive

---

### 5. Extend AppointmentService

**File**: `src/services/appointment_service.py` (EXTEND)

**Changes to `__init__`**:
```python
def __init__(
    self,
    google_calendar_client: GoogleCalendarClient,
    dentist_service: DentistService,  # NEW
    clinic_timezone: str = "America/Argentina/Buenos_Aires",
):
    self.google_calendar_client = google_calendar_client
    self.dentist_service = dentist_service  # NEW
    self.clinic_timezone = clinic_timezone
```

**Update `get_available_slots` method**:
```python
async def get_available_slots(
    self,
    session: AsyncSession,
    dentist_id: UUID,  # NEW parameter
) -> List[AvailableSlot]:
    """Get available slots for specific dentist."""
    # 1. Get dentist and calendar_id via DentistService
    dentist = await self.dentist_service.get_dentist_by_id(session, dentist_id)
    # 2. Call Google Calendar with dentist's calendar_id
    # 3. Return filtered slots
```

**Update `book_appointment` method**:
```python
async def book_appointment(
    self,
    session: AsyncSession,
    patient_user_id: UUID,
    dentist_id: UUID,  # NEW parameter
    appointment_date: date,
    start_time: time,
    reason: str,
) -> Appointment:
    """Book appointment with specific dentist."""
    # 1. Validate dentist exists and is active
    # 2. Validate slot is still available for this dentist
    # 3. Create appointment with dentist_id
    # 4. Persist to DB
```

---

### 6. Extend AppointmentRouter

**File**: `src/services/appointment_router.py` (EXTEND)

**Add dentist selection step**:
```python
# In conversation flow, after user selects "1 - Appointment":

async def handle_appointment_selection(
    session: AsyncSession,
    user_id: UUID,
    telegram_user: TelegramUser,
) -> str:
    """Route to dentist selection or straight to slots (if only one dentist)."""
    
    active_dentists = await self.dentist_service.get_active_dentists(session)
    
    if len(active_dentists) == 0:
        return "No dentists available. Please contact secretary."
    
    if len(active_dentists) == 1:
        # Auto-select single dentist
        selected_dentist = active_dentists[0]
        await self.conversation_manager.set_step(
            session, user_id, "WAITING_FOR_APPOINTMENT",
            {"selected_dentist_id": str(selected_dentist.id)}
        )
        return await self.show_available_slots(session, selected_dentist.id)
    
    # Multiple dentists: show selection menu
    dentist_list = "\n".join(
        f"{i+1}. {d.name}" for i, d in enumerate(active_dentists)
    )
    await self.conversation_manager.set_step(
        session, user_id, "SELECTING_DENTIST",
        {"available_dentists": [str(d.id) for d in active_dentists]}
    )
    return f"Which dentist would you like to book with?\n{dentist_list}"

async def handle_dentist_selected(
    session: AsyncSession,
    user_id: UUID,
    selection_number: str,
) -> str:
    """Process dentist selection and move to slot display."""
    
    state = await self.conversation_manager.get_state(session, user_id)
    dentists = state.step_context.get("available_dentists", [])
    
    try:
        idx = int(selection_number) - 1
        selected_dentist_id = UUID(dentists[idx])
    except (ValueError, IndexError):
        return "Invalid selection. Please try again."
    
    await self.conversation_manager.set_step(
        session, user_id, "WAITING_FOR_APPOINTMENT",
        {"selected_dentist_id": str(selected_dentist_id)}
    )
    
    return await self.show_available_slots(session, selected_dentist_id)

async def show_available_slots(
    self,
    session: AsyncSession,
    dentist_id: UUID,
) -> str:
    """Display available slots for selected dentist."""
    slots = await self.appointment_service.get_available_slots(
        session, dentist_id
    )
    # ... format and return slots ...
```

---

### 7. Extend MenuRouter

**File**: `src/services/menu_router.py` (EXTEND)

**Update appointment option handling**:
```python
# When user sends "1" (appointment option):
if user_input == "1":
    return await self.appointment_router.handle_appointment_selection(
        session, user_id, telegram_user
    )
```

---

### 8. Extend Conversation Manager

**File**: `src/services/conversation_manager.py` (EXTEND, if needed)

**Ensure `set_step` / `get_step` handle new conversation states**:
- `SELECTING_DENTIST`: Track which dentists are available, which is selected
- Update `step_context` JSON structure to include `selected_dentist_id`

**No schema changes required** (uses existing JSON field).

---

### 9. Update Schemas

**File**: `src/schemas/appointment.py` (EXTEND)

```python
class AppointmentCreate(BaseModel):
    dentist_id: UUID  # NEW
    appointment_date: date
    start_time: time
    reason: str

class AppointmentResponse(BaseModel):
    id: UUID
    dentist_id: UUID  # NEW
    appointment_date: date
    start_time: time
    reason: str
    status: AppointmentStatusEnum
    # ... etc

# Update AvailableSlot if needed to include dentist context
```

**File**: `src/schemas/dentist.py` (NEW)

```python
from pydantic import BaseModel
from uuid import UUID

class DentistResponse(BaseModel):
    id: UUID
    name: str
    calendar_id: str
    active_status: bool
    
    class Config:
        from_attributes = True

class DentistCreate(BaseModel):
    name: str
    calendar_id: str
    active_status: bool = True
```

---

## Testing Strategy

### Unit Tests (NEW/EXTENDED)

**File**: `tests/unit/test_dentist_service.py`
- Test `get_active_dentists()` returns only active dentists
- Test `get_dentist_by_id()` with valid/invalid IDs
- Test error cases (DentistNotFoundError, DentistInactiveError)

**File**: `tests/unit/test_appointment_service.py` (EXTEND)
- Add tests with `dentist_id` parameter
- Test slot availability per dentist (same time, different dentists should both be available)
- Test booking with invalid dentist_id

**File**: `tests/unit/test_appointment_router.py` (EXTEND)
- Test single-dentist auto-selection
- Test multi-dentist selection menu display
- Test invalid dentist selection handling

### Integration Tests (NEW)

**File**: `tests/integration/test_multi_dentist_booking_flow.py`
- Full end-to-end: menu → dentist selection → slot display → booking with Dentist A
- Full end-to-end: same flow with Dentist B, verify appointments don't conflict
- Test concurrent bookings on same slot but different dentists succeed
- Test concurrent bookings on same slot AND same dentist fail (conflict)

### Test Data Setup

```python
# Create test dentists
@pytest.fixture
async def test_dentists(session: AsyncSession):
    hector = Dentist(
        name="Hector",
        calendar_id="hector@clinic.calendar.google.com",
        active_status=True,
    )
    fulano = Dentist(
        name="Fulano",
        calendar_id="fulano@clinic.calendar.google.com",
        active_status=True,
    )
    session.add_all([hector, fulano])
    await session.commit()
    return [hector, fulano]
```

---

## Deployment Checklist

- [ ] Create and test Alembic migration
- [ ] Add test dentists to dev/staging databases
- [ ] Test backward compatibility (single-dentist flows)
- [ ] Run full test suite (unit + integration)
- [ ] Update API documentation (if exposed externally)
- [ ] Deploy migration to production
- [ ] Deploy new code
- [ ] Monitor appointment booking flow (latency, errors)
- [ ] Verify dentist selection menu displays correctly

---

## Configuration

**Environment Variables** (if needed):
- No new env vars required
- Dentist list managed via database (not config)

---

## Creating Dentists (Adding Doctors)

### Quick Command (Recommended)

Add a new doctor with one simple command:

```bash
python scripts/seed_dentists.py "Doctor Name" "calendar_id@clinic.calendar.google.com"
```

#### Examples:

**Add Hector:**
```bash
python scripts/seed_dentists.py "Hector" "hector@clinic.calendar.google.com"
```

**Output:**
```
✅ Creado dentista: Hector (ID: 550e8400-e29b-41d4-a716-446655440000)
```

**Add Fulano:**
```bash
python scripts/seed_dentists.py "Fulano" "fulano@clinic.calendar.google.com"
```

**Add Dr. García:**
```bash
python scripts/seed_dentists.py "Dr. García" "garcia@clinic.calendar.google.com"
```

### What Happens After Adding a Doctor

✅ **Immediately available** in the appointment booking menu  
✅ **Calendar linked** to Google Calendar with provided calendar_id  
✅ **No code changes** required - purely database-driven  
✅ **Appears in selection menu** on next user interaction

### Manual Database Insert (Alternative)

If you prefer direct SQL:

```sql
INSERT INTO dentists (name, calendar_id, active_status) 
VALUES 
    ('Hector', 'hector@clinic.calendar.google.com', TRUE),
    ('Fulano', 'fulano@clinic.calendar.google.com', TRUE);
```

### Bulk Import from JSON File

For adding multiple doctors at once:

```bash
# Create dentists.json (see dentists.json.example)
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

---

## Verifying Doctors Are Created

### Via Bot Menu

Send "1" to the bot:
```
User sends: 1

Bot responds:
"¿A qué odontólogo deseas pedir turno?

1. Hector
2. Fulano"  ← Your doctors appear here
```

### Via Database Query

```bash
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
            "SELECT id, name, calendar_id, active_status FROM dentists ORDER BY name"
        ))
        print("\n📋 Doctors in Database:\n")
        for row in result:
            status = "🟢 ACTIVE" if row[3] else "🔴 INACTIVE"
            print(f"{row[1]:20} → {row[2]:40} {status}")
    await engine.dispose()

asyncio.run(list_dentists())
EOF
```

**Output:**
```
📋 Doctors in Database:

Fulano               → fulano@clinic.calendar.google.com  🟢 ACTIVE
Hector               → hector@clinic.calendar.google.com  🟢 ACTIVE
```

---

## Managing Doctors

### Deactivate a Doctor (Soft Delete)

```bash
python3 << 'EOF'
import asyncio
from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.config import settings

async def deactivate_doctor(name):
    engine = create_async_engine(settings.database_url)
    async_session = async_sessionmaker(engine, class_=AsyncSession)
    async with async_session() as session:
        await session.execute(
            update("dentists")
            .where(text(f"name = '{name}'"))
            .values(active_status=False)
        )
        await session.commit()
        print(f"✅ Deactivated: {name}")
    await engine.dispose()

asyncio.run(deactivate_doctor("Hector"))
EOF
```

### Update Doctor's Calendar

```bash
python3 << 'EOF'
import asyncio
from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.config import settings

async def update_calendar(name, new_calendar_id):
    engine = create_async_engine(settings.database_url)
    async_session = async_sessionmaker(engine, class_=AsyncSession)
    async with async_session() as session:
        await session.execute(
            update("dentists")
            .where(text(f"name = '{name}'"))
            .values(calendar_id=new_calendar_id)
        )
        await session.commit()
        print(f"✅ Updated {name} → {new_calendar_id}")
    await engine.dispose()

asyncio.run(update_calendar("Hector", "hector.new@clinic.calendar.google.com"))
EOF
```

---

## **Dentist Initial Setup** (Legacy - use command above)

```python
# OLD - Script: scripts/seed_dentists.py
INSERT INTO dentists (name, calendar_id) VALUES
('Hector', 'hector@clinic.calendar.google.com'),
('Fulano', 'fulano@clinic.calendar.google.com');
```

---

## Key Design Decisions Recap

1. **Dentist storage**: Database table (not env vars/hardcoded)
2. **Selection flow**: Conversation-based (menu step for dentist selection)
3. **Calendar API**: Reuse existing GoogleCalendarClient with parameter
4. **Uniqueness**: Constraint includes `dentist_id` (per-dentist slots)
5. **Auto-selection**: Single-dentist clinics skip menu (backward compatible)
6. **Error handling**: Matches existing patterns (GoogleCalendarError, etc.)
7. **Testing**: Unit + integration tests; test concurrent scenarios

---

## Related Documentation

- **Data Model**: [data-model.md](data-model.md)
- **Research & Decisions**: [research.md](research.md)
- **Specification**: [spec.md](spec.md)
- **Service Contracts**: [contracts/](contracts/) (if defined)
