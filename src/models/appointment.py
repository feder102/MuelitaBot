"""Appointment ORM model for appointment booking feature."""
from enum import Enum
from datetime import datetime, date, time
from uuid import uuid4
from sqlalchemy import Column, String, Date, Time, DateTime, BigInteger, ForeignKey, Enum as SQLEnum, Text, CheckConstraint, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.db import Base


class AppointmentStatusEnum(str, Enum):
    """Appointment lifecycle status."""

    PENDING = "PENDING"  # Booked, awaiting doctor confirmation
    CONFIRMED = "CONFIRMED"  # Doctor confirmed
    COMPLETED = "COMPLETED"  # Appointment occurred
    CANCELLED = "CANCELLED"  # User or doctor cancelled


class Appointment(Base):
    """Appointment entity for doctor's calendar.

    Stores booked appointment slots with patient info and consultation reason.
    """

    __tablename__ = "appointments"

    # Identifiers
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Booking details
    patient_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("telegram_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    appointment_date = Column(Date, nullable=False, index=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    reason = Column(String(150), nullable=False)

    # Staff tracking
    created_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("telegram_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_by_phone = Column(String(20), nullable=True)

    # Status & timestamps
    status = Column(
        SQLEnum(AppointmentStatusEnum),
        nullable=False,
        default=AppointmentStatusEnum.PENDING,
        index=True,
    )
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
        CheckConstraint(
            "end_time = start_time + INTERVAL '1 hour'", name="ck_appointment_duration"
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Appointment(id={self.id}, patient_user_id={self.patient_user_id}, "
            f"date={self.appointment_date}, time={self.start_time}, status={self.status})>"
        )
