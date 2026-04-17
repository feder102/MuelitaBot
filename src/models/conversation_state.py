"""ConversationState ORM model."""
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import relationship
import uuid

from src.db import Base


class ConversationStateEnum(str, Enum):
    """States in the user conversation flow."""

    # Feature 001: Webhook Menu
    AWAITING_MENU = "AWAITING_MENU"
    AWAITING_SELECTION = "AWAITING_SELECTION"
    APPOINTMENT_SELECTED = "APPOINTMENT_SELECTED"
    SECRETARY_SELECTED = "SECRETARY_SELECTED"

    # Feature 002: Appointment Booking
    AWAITING_SLOT_SELECTION = "AWAITING_SLOT_SELECTION"  # User viewing available slots
    AWAITING_REASON_TEXT = "AWAITING_REASON_TEXT"  # User entering consultation reason
    APPOINTMENT_CONFIRMED = "APPOINTMENT_CONFIRMED"  # Appointment booking confirmed

    # Feature 003: Multi-Dentist Booking
    SELECTING_DENTIST = "SELECTING_DENTIST"  # User selecting which dentist to book with

    # Feature 004: Cancel Appointment
    SELECTING_CANCELLATION_APPOINTMENT = "SELECTING_CANCELLATION_APPOINTMENT"  # User viewing cancellable appointment list
    AWAITING_CANCELLATION_CONFIRMATION = "AWAITING_CANCELLATION_CONFIRMATION"  # User confirming which appointment to cancel

    # Terminal states
    COMPLETED = "COMPLETED"
    INACTIVE = "INACTIVE"


class ConversationState(Base):
    """Tracks the current state of a user's interaction with the bot."""

    __tablename__ = "conversation_state"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("telegram_users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    current_state = Column(
        ENUM(ConversationStateEnum),
        nullable=False,
        default=ConversationStateEnum.AWAITING_MENU,
    )
    last_interaction = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
    menu_display_count = Column(Integer, nullable=False, default=0)
    context_data = Column(JSON, nullable=True, default={})  # Stores conversation context (e.g., available slots)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    user = relationship("TelegramUser", back_populates="conversation_state")

    def __repr__(self):
        return f"<ConversationState(user_id={self.user_id}, current_state={self.current_state})>"
