"""AuditLog ORM model for immutable audit trail."""
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import relationship
import uuid

from src.db import Base


class AuditActionEnum(str, Enum):
    """Types of audit actions."""

    WEBHOOK_RECEIVED = "WEBHOOK_RECEIVED"
    SIGNATURE_VALIDATION_FAILED = "SIGNATURE_VALIDATION_FAILED"
    MESSAGE_PARSED = "MESSAGE_PARSED"
    MENU_DISPLAYED = "MENU_DISPLAYED"
    MENU_SELECTION_MADE = "MENU_SELECTION_MADE"
    APPOINTMENT_ROUTED = "APPOINTMENT_ROUTED"
    SECRETARY_ROUTED = "SECRETARY_ROUTED"
    INVALID_SELECTION = "INVALID_SELECTION"
    DATABASE_ERROR = "DATABASE_ERROR"
    TELEGRAM_API_ERROR = "TELEGRAM_API_ERROR"


class AuditStatusEnum(str, Enum):
    """Status of audit action."""

    SUCCESS = "SUCCESS"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    ERROR = "ERROR"


class AuditLog(Base):
    """Immutable audit trail of all user interactions and webhook events."""

    __tablename__ = "audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("telegram_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action = Column(String(50), nullable=False, index=True)
    status = Column(ENUM(AuditStatusEnum), nullable=False, index=True)
    message_text = Column(Text, nullable=True)
    response_text = Column(Text, nullable=True)
    error_detail = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv4 (15) or IPv6 (39) + buffer
    request_headers = Column(String, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    # Relationships
    user = relationship("TelegramUser", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog(id={self.id}, action={self.action}, status={self.status})>"
