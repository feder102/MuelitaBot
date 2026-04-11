"""Dentist ORM model for multi-dentist appointment booking feature."""
from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, Boolean, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.db import Base


class Dentist(Base):
    """Dentist entity representing a dental professional in the system.

    Each dentist has their own Google Calendar with a unique calendar_id.
    Dentists can be activated/deactivated without deleting records.
    """

    __tablename__ = "dentists"

    # Identifiers
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Dentist information
    name = Column(String(100), nullable=False, unique=True, index=True)
    calendar_id = Column(String(255), nullable=False, unique=True)

    # Status & timestamps
    active_status = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    appointments = relationship("Appointment", back_populates="dentist")

    # Table arguments (indexes, constraints)
    __table_args__ = (
        Index('idx_dentist_active_status', 'active_status'),
        Index('idx_dentist_name', 'name'),
    )

    def __repr__(self) -> str:
        return f"<Dentist(id={self.id}, name={self.name}, calendar_id={self.calendar_id}, active={self.active_status})>"
