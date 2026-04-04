# Phase 1 Design: Data Model & Schema

**Date**: 2026-04-04  
**Feature**: [Appointment Booking with Google Calendar](spec.md)  
**Architecture**: SQLAlchemy ORM with PostgreSQL

---

## Entity Relationships

```
TelegramUser (existing)
    ├── 1:N ──> Appointment
    └── 1:N ──> ConversationState (existing)

Appointment (NEW)
    ├── N:1 ──> TelegramUser (patient_user_id)
    ├── N:1 ──> TelegramUser (created_by_user_id, optional - staff)
    ├── 1:1 ──> ConversationState (in_progress conversation, optional)
    └── (Implicit) Google Calendar slot (not stored, computed on-the-fly)

CachedCalendarSlot (NEW, optional)
    └── Schedule of available slots for caching
```

---

## Entity: Appointment

**Purpose**: Store booked appointment details for doctor reference and patient confirmation

**Table Name**: `appointments`

### Fields

| Field | Type | Constraints | Purpose |
|-------|------|-----------|---------|
| `id` | UUID | PK | Unique appointment identifier |
| `patient_user_id` | BigInt | FK → `telegram_users.id`, NOT NULL | Which patient/user booked this appointment |
| `appointment_date` | Date | NOT NULL | Date of appointment (stored in UTC, displayed in clinic TZ) |
| `start_time` | Time | NOT NULL | Start time in UTC (e.g., 11:00 for 08:00 ART) |
| `end_time` | Time | NOT NULL | End time in UTC (always start_time + 1 hour) |
| `reason` | VARCHAR(150) | NOT NULL | Consultation reason/chief complaint (max 150 chars per spec) |
| `created_by_user_id` | BigInt | FK → `telegram_users.id`, nullable | Telegram staff/admin user if created via integration (tracks who booked) |
| `created_by_phone` | VARCHAR(20) | nullable | Phone number of staff member who created appointment (alternative to user_id) |
| `status` | ENUM | NOT NULL, DEFAULT='PENDING' | Appointment lifecycle: PENDING → CONFIRMED → COMPLETED → CANCELLED |
| `created_at` | DateTime | NOT NULL, DEFAULT=now() | Timestamp appointment was booked |
| `updated_at` | DateTime | NOT NULL, DEFAULT=now(), ON UPDATE | Last modified timestamp |
| `confirmed_at` | DateTime | nullable | When doctor confirmed appointment (for v2 workflow) |
| `notes` | Text | nullable | Doctor's internal notes (added later, not by user) |

### Constraints

- **Primary Key**: `id`
- **Foreign Keys**:
  - `patient_user_id` → `telegram_users.id` (NOT NULL, ON DELETE CASCADE)
  - `created_by_user_id` → `telegram_users.id` (nullable, ON DELETE SET NULL)
- **Unique**: `(appointment_date, start_time)` - **CRITICAL for double-booking prevention**
- **Check**: `end_time = start_time + INTERVAL '1 hour'` (all appointments 1 hour)
- **Check**: `reason` length ≤ 150 characters
- **Check**: `status IN ('PENDING', 'CONFIRMED', 'COMPLETED', 'CANCELLED')`
- **Indexes**:
  - `idx_patient_user_id` on `patient_user_id` (query appointments by user)
  - `idx_appointment_date` on `appointment_date` (query by date range)
  - `idx_status` on `status` (filter by status)
  - `idx_created_by_user_id` on `created_by_user_id` (audit trail)

### SQLAlchemy Model Definition

```python
# src/models/appointment.py
from enum import Enum
from datetime import datetime, date, time
from uuid import uuid4
from sqlalchemy import Column, String, Date, Time, DateTime, BigInteger, ForeignKey, Enum as SQLEnum, Text, CheckConstraint, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from src.db import Base

class AppointmentStatusEnum(str, Enum):
    """Appointment lifecycle status."""
    PENDING = "PENDING"        # Booked, awaiting doctor confirmation
    CONFIRMED = "CONFIRMED"    # Doctor confirmed
    COMPLETED = "COMPLETED"    # Appointment occurred
    CANCELLED = "CANCELLED"    # User or doctor cancelled

class Appointment(Base):
    """
    Appointment entity for doctor's calendar.
    Stores booked appointment slots with patient info and consultation reason.
    """
    __tablename__ = "appointments"

    # Identifiers
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    
    # Booking details
    patient_user_id = Column(BigInteger, ForeignKey("telegram_users.id", ondelete="CASCADE"), nullable=False, index=True)
    appointment_date = Column(Date, nullable=False, index=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    reason = Column(String(150), nullable=False)
    
    # Staff tracking
    created_by_user_id = Column(BigInteger, ForeignKey("telegram_users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_by_phone = Column(String(20), nullable=True)
    
    # Status & timestamps
    status = Column(SQLEnum(AppointmentStatusEnum), nullable=False, default=AppointmentStatusEnum.PENDING, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    confirmed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Relationships
    patient = relationship("TelegramUser", foreign_keys=[patient_user_id], backref="appointments")
    created_by = relationship("TelegramUser", foreign_keys=[created_by_user_id])
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("appointment_date", "start_time", name="uq_appointment_slot"),
        CheckConstraint("char_length(reason) <= 150", name="ck_reason_length"),
        CheckConstraint("end_time = start_time + INTERVAL '1 hour'", name="ck_appointment_duration"),
    )
    
    def __repr__(self) -> str:
        return f"<Appointment(id={self.id}, patient_user_id={self.patient_user_id}, date={self.appointment_date}, time={self.start_time}, status={self.status})>"
```

---

## Entity: CachedCalendarSlot (Optional, for caching strategy)

**Purpose**: Cache Google Calendar API responses to meet <3 second performance goal

**Table Name**: `cached_calendar_slots`

**Note**: Optional for v1 (database queries are already <100ms). Recommended to add for reliability + API quota management.

### Fields

| Field | Type | Constraints | Purpose |
|-------|------|-----------|---------|
| `id` | UUID | PK | Cache entry ID |
| `slot_date` | Date | NOT NULL | Date of available slot |
| `start_time` | Time | NOT NULL | Start time (UTC) |
| `end_time` | Time | NOT NULL | End time (UTC) |
| `is_available` | Boolean | NOT NULL, DEFAULT=true | Slot is available (true) or booked (false) |
| `is_booked_locally` | Boolean | NOT NULL, DEFAULT=false | User booked this slot in current system (optimistic flag) |
| `cached_at` | DateTime | NOT NULL, DEFAULT=now() | When this cache entry was fetched from Google Calendar API |
| `expires_at` | DateTime | NOT NULL | When this cache entry expires (now + 1 hour TTL) |
| `source` | ENUM | NOT NULL | 'GOOGLE_CALENDAR' or 'LOCAL_BOOKING' (indicates origin) |

### Constraints

- **Primary Key**: `id`
- **Unique**: `(slot_date, start_time)` (only one entry per slot)
- **Check**: `end_time = start_time + INTERVAL '1 hour'`
- **Index**: `idx_expires_at` (for cleanup queries)
- **Index**: `idx_slot_date, idx_is_available` (for availability queries)

### Usage Pattern

```python
# Query available slots for tomorrow
from datetime import datetime, timedelta

tomorrow = datetime.utcnow().date() + timedelta(days=1)

# Get fresh cache (not expired)
available_slots = await db.execute(
    select(CachedCalendarSlot).filter(
        CachedCalendarSlot.slot_date == tomorrow,
        CachedCalendarSlot.is_available == True,
        CachedCalendarSlot.expires_at > datetime.utcnow()
    ).order_by(CachedCalendarSlot.start_time)
)

# If no fresh cache, fetch from Google Calendar API and insert/update
```

**Optional - Skip for v1**: If slot caching adds complexity, use on-demand API fetching with simple error handling. The unique constraint on `appointments(appointment_date, start_time)` prevents double-booking regardless.

---

## Entity: Pydantic Schemas (for API validation)

**File**: `src/schemas/appointment.py`

```python
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, date, time
from enum import Enum
from typing import Optional

class AppointmentStatusEnum(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class SlotRequest(BaseModel):
    """User selecting a time slot."""
    slot_number: int = Field(..., gt=0, description="1-indexed slot selection")
    
class ReasonRequest(BaseModel):
    """User providing consultation reason."""
    reason: str = Field(..., min_length=1, max_length=150, description="Consultation reason (max 150 chars)")
    
    @field_validator("reason")
    @classmethod
    def reason_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Reason cannot be empty or whitespace-only")
        return v.strip()

class AppointmentCreate(BaseModel):
    """Internal schema for creating appointment (after validation)."""
    patient_user_id: int
    appointment_date: date
    start_time: time
    reason: str
    created_by_user_id: Optional[int] = None
    created_by_phone: Optional[str] = None

class AppointmentResponse(BaseModel):
    """Appointment details returned to user."""
    id: str
    appointment_date: date
    start_time: time
    end_time: time
    reason: str
    status: AppointmentStatusEnum
    created_at: datetime
    
    class Config:
        from_attributes = True

class AvailableSlot(BaseModel):
    """Available appointment slot from Google Calendar."""
    slot_number: int
    date_display: str      # e.g., "Lunes 08 de Abril"
    time_display: str      # e.g., "08:00-09:00"
    start_time: time       # e.g., 11:00 (UTC)
    end_time: time         # e.g., 12:00 (UTC)

class SlotsResponse(BaseModel):
    """List of available slots returned to user."""
    slots: list[AvailableSlot]
    message: str           # e.g., "Elige un turno disponible"
```

---

## Enum Definitions

### AppointmentStatusEnum
- **PENDING**: Booked but not confirmed by doctor (initial state)
- **CONFIRMED**: Doctor reviewed and confirmed (future enhancement)
- **COMPLETED**: Appointment occurred
- **CANCELLED**: Cancelled by user or doctor

### SourceEnum (for CachedCalendarSlot, optional)
- **GOOGLE_CALENDAR**: Fetched from Google Calendar API
- **LOCAL_BOOKING**: Local system inference (user booked this slot)

---

## Migration Strategy

**File**: `migrations/versions/002_add_appointments.py` (Alembic migration)

```python
"""Add appointments table.

Revision ID: 002
Revises: 001_initial_schema
Create Date: 2026-04-04

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade() -> None:
    # Create enum type
    appointment_status = postgresql.ENUM(
        'PENDING', 'CONFIRMED', 'COMPLETED', 'CANCELLED',
        name='appointmentstatus'
    )
    appointment_status.create(op.get_bind(), checkfirst=True)
    
    # Create appointments table
    op.create_table(
        'appointments',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('patient_user_id', sa.BigInteger, nullable=False),
        sa.Column('appointment_date', sa.Date, nullable=False),
        sa.Column('start_time', sa.Time, nullable=False),
        sa.Column('end_time', sa.Time, nullable=False),
        sa.Column('reason', sa.String(150), nullable=False),
        sa.Column('created_by_user_id', sa.BigInteger, nullable=True),
        sa.Column('created_by_phone', sa.String(20), nullable=True),
        sa.Column('status', appointment_status, nullable=False, server_default='PENDING'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('confirmed_at', sa.DateTime, nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['patient_user_id'], ['telegram_users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['telegram_users.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('appointment_date', 'start_time', name='uq_appointment_slot'),
        sa.CheckConstraint("char_length(reason) <= 150", name='ck_reason_length'),
        sa.CheckConstraint("end_time = start_time + INTERVAL '1 hour'", name='ck_appointment_duration'),
    )
    
    # Create indexes
    op.create_index('idx_patient_user_id', 'appointments', ['patient_user_id'])
    op.create_index('idx_appointment_date', 'appointments', ['appointment_date'])
    op.create_index('idx_status', 'appointments', ['status'])
    op.create_index('idx_created_by_user_id', 'appointments', ['created_by_user_id'])

def downgrade() -> None:
    op.drop_table('appointments')
    appointment_status = postgresql.ENUM('PENDING', 'CONFIRMED', 'COMPLETED', 'CANCELLED', name='appointmentstatus')
    appointment_status.drop(op.get_bind(), checkfirst=True)
```

---

## State Machine: Appointment Lifecycle

```
PENDING ──[doctor confirms]──> CONFIRMED ──[appointment occurs]──> COMPLETED
   ↓                                  ↓
   └────────[user/doctor cancels]────┴──────────────> CANCELLED
```

**Current Implementation (v1)**: Appointments created in PENDING state. User sees confirmation but no doctor workflow.
**Future (v2)**: Add doctor admin interface to transition PENDING → CONFIRMED → COMPLETED

---

## Validation Rules

### Appointment Creation

1. **Date**: Must be >= tomorrow (no same-day booking)
2. **Time**: Must be within Mon-Fri, 08:00-13:00 (clinic hours)
3. **Reason**: 1-150 characters, non-empty
4. **Unique Slot**: No appointment already exists for (date, start_time)
5. **User Exists**: patient_user_id must exist in telegram_users

### Concurrency Safety

- **Database constraint** enforces UNIQUE(appointment_date, start_time) at transaction level
- If concurrent inserts attempt same slot → second transaction fails with `IntegrityError`
- Application retries with updated slot list

---

## Audit Trail

Appointments table is audit-logged via existing `audit_log` table:

```python
# In appointment_service.py after booking
await audit_log_service.log(
    action=AuditActionEnum.APPOINTMENT_CREATED,
    user_id=patient_user_id,
    resource_type="Appointment",
    resource_id=appointment.id,
    metadata={"reason": appointment.reason, "slot": appointment.start_time}
)
```

---

## Performance Considerations

1. **Indexes on Foreign Keys**: `patient_user_id`, `created_by_user_id` indexed for joins
2. **Indexes on Filters**: `appointment_date`, `status` indexed for queries
3. **Unique Constraint**: Enforced at database level for concurrent safety
4. **Query Optimization**:
   - No N+1 queries: Use `joinedload()` for TelegramUser relationships
   - No sequential scans: Always filter by indexed columns
5. **Example Query** (O(log N)):
   ```python
   result = await session.execute(
       select(Appointment).where(
           Appointment.appointment_date == target_date,
           Appointment.patient_user_id == user_id
       ).options(joinedload(Appointment.patient))
   )
   ```

---

## Next Steps

1. ✅ Create migration file: `migrations/versions/002_add_appointments.py`
2. ✅ Define models in: `src/models/appointment.py`
3. ✅ Define schemas in: `src/schemas/appointment.py`
4. ⬜ Create contracts in: `specs/002-appointment-booking/contracts/`
5. ⬜ Create quickstart guide: `specs/002-appointment-booking/quickstart.md`

