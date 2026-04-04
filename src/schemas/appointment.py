"""Pydantic schemas for appointment booking feature."""
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, date, time
from enum import Enum
from typing import Optional


class AppointmentStatusEnum(str, Enum):
    """Appointment status options."""

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
        """Validate reason is not empty or whitespace-only."""
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
    date: date  # Date of the slot
    date_display: str  # e.g., "Lunes 08 de Abril"
    time_display: str  # e.g., "08:00-09:00"
    start_time: time  # e.g., 11:00 (UTC)
    end_time: time  # e.g., 12:00 (UTC)


class SlotsResponse(BaseModel):
    """List of available slots returned to user."""

    slots: list[AvailableSlot]
    message: str  # e.g., "Elige un turno disponible"
