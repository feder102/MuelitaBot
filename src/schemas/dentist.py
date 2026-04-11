"""Pydantic schemas for dentist operations."""
from uuid import UUID
from pydantic import BaseModel, Field


class DentistCreate(BaseModel):
    """Schema for creating a new dentist."""

    name: str = Field(..., min_length=1, max_length=100, description="Dentist name")
    calendar_id: str = Field(..., min_length=1, max_length=255, description="Google Calendar ID")
    active_status: bool = Field(default=True, description="Whether dentist is active for bookings")


class DentistUpdate(BaseModel):
    """Schema for updating a dentist."""

    name: str | None = Field(None, min_length=1, max_length=100, description="Dentist name")
    calendar_id: str | None = Field(None, min_length=1, max_length=255, description="Google Calendar ID")
    active_status: bool | None = Field(None, description="Whether dentist is active for bookings")


class DentistResponse(BaseModel):
    """Schema for dentist response (read model)."""

    id: UUID
    name: str
    calendar_id: str
    active_status: bool

    class Config:
        from_attributes = True
