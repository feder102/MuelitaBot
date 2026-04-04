"""Pydantic schemas for Telegram webhook requests and responses."""
from typing import Optional
from pydantic import BaseModel, Field


class Chat(BaseModel):
    """Telegram Chat object."""

    id: int = Field(..., description="Unique identifier for this chat")
    type: str = Field(..., description="Type of chat (private, group, supergroup, channel)")
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None


class User(BaseModel):
    """Telegram User object."""

    id: int
    is_bot: bool = False
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None


class Message(BaseModel):
    """Telegram Message object."""

    message_id: int
    date: int = Field(..., description="Unix timestamp")
    chat: Chat
    text: Optional[str] = None
    from_: Optional[User] = Field(None, alias="from")

    class Config:
        populate_by_name = True


class Update(BaseModel):
    """Telegram Update object (webhook request body)."""

    update_id: int = Field(..., description="Unique identifier for this update")
    message: Optional[Message] = None

    class Config:
        populate_by_name = True


class WebhookResponse(BaseModel):
    """Response from webhook endpoint."""

    ok: bool = Field(..., description="Whether the request was successful")
    error_code: Optional[int] = None
    description: Optional[str] = None
