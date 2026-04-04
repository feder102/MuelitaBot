"""TelegramUser ORM model."""
from datetime import datetime
from sqlalchemy import Column, String, BigInteger, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from src.db import Base


class TelegramUser(Base):
    """Represents a Telegram user who has interacted with the bot."""

    __tablename__ = "telegram_users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    telegram_user_id = Column(BigInteger, unique=True, nullable=False, index=True)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=True)
    username = Column(String(255), nullable=True, unique=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    conversation_state = relationship(
        "ConversationState",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    audit_logs = relationship(
        "AuditLog",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<TelegramUser(id={self.id}, telegram_user_id={self.telegram_user_id}, first_name={self.first_name})>"
