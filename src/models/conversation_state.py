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

    AWAITING_MENU = "AWAITING_MENU"
    AWAITING_SELECTION = "AWAITING_SELECTION"
    APPOINTMENT_SELECTED = "APPOINTMENT_SELECTED"
    SECRETARY_SELECTED = "SECRETARY_SELECTED"
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
    metadata = Column(JSON, nullable=True, default={})
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    user = relationship("TelegramUser", back_populates="conversation_state")

    def __repr__(self):
        return f"<ConversationState(user_id={self.user_id}, current_state={self.current_state})>"
